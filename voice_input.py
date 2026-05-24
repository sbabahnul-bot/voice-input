import os
import io
import time
import threading
import numpy as np
import sounddevice as sd
import pyperclip
import httpx
import keyboard
from scipy.io import wavfile
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LANGUAGE = os.getenv("LANGUAGE", "ru")
SAMPLE_RATE = 16000
CHUNK_SIZE = 512

SPEECH_THRESHOLD = 600       # уровень громкости для определения речи
SPEECH_START_CHUNKS = 6      # ~190ms речи чтобы начать запись
SILENCE_END_CHUNKS = 35      # ~1.1s тишины чтобы закончить запись
PRE_BUFFER_SIZE = 10         # буфер до начала речи (~320ms)


def get_rms(chunk):
    return np.sqrt(np.mean(chunk.astype(np.float32) ** 2))


def transcribe_and_paste(frames):
    audio = np.concatenate(frames).flatten()
    print("[...] отправляю в Deepgram...", flush=True)
    try:
        buf = io.BytesIO()
        wavfile.write(buf, SAMPLE_RATE, audio)
        buf.seek(0)
        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/wav",
            },
            params={"model": "nova-2", "language": LANGUAGE, "punctuate": "true"},
            content=buf.read(),
            timeout=30.0,
            verify=False,
        )
        response.raise_for_status()
        text = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except Exception as e:
        print(f"[!] ошибка: {e}", flush=True)
        return

    if not text:
        print("[!] ничего не распознано", flush=True)
        return

    print(f"[OK] {text}", flush=True)
    pyperclip.copy(text)
    time.sleep(0.15)
    keyboard.send("ctrl+v")


def calibrate(seconds=1.5):
    print(f"[калибровка] {seconds}с тишины...", flush=True)
    chunks = []

    def cb(indata, frames, t, status):
        chunks.append(indata[:, 0].copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        blocksize=CHUNK_SIZE, callback=cb):
        time.sleep(seconds)

    if chunks:
        noise = np.mean([get_rms(c) for c in chunks])
        threshold = max(noise * 4, 300)
        print(f"[калибровка] уровень шума: {noise:.0f}, порог: {threshold:.0f}", flush=True)
        return threshold
    return SPEECH_THRESHOLD


def run():
    threshold = calibrate()

    state = "silent"
    speech_counter = 0
    silence_counter = 0
    recording_frames = []
    pre_buffer = []
    busy = False

    def callback(indata, frames, t, status):
        nonlocal state, speech_counter, silence_counter
        nonlocal recording_frames, pre_buffer, busy

        if busy:
            return

        chunk = indata[:, 0].copy()
        rms = get_rms(chunk)
        is_speech = rms > threshold

        if state == "silent":
            pre_buffer.append(chunk)
            if len(pre_buffer) > PRE_BUFFER_SIZE:
                pre_buffer.pop(0)
            if is_speech:
                speech_counter += 1
                if speech_counter >= SPEECH_START_CHUNKS:
                    state = "recording"
                    recording_frames = list(pre_buffer)
                    print("[mic] запись...", flush=True)
            else:
                speech_counter = 0

        elif state == "recording":
            recording_frames.append(chunk)
            if not is_speech:
                silence_counter += 1
                if silence_counter >= SILENCE_END_CHUNKS:
                    state = "silent"
                    speech_counter = 0
                    silence_counter = 0
                    frames_copy = recording_frames.copy()
                    recording_frames = []
                    busy = True
                    def process():
                        nonlocal busy
                        transcribe_and_paste(frames_copy)
                        busy = False
                    threading.Thread(target=process, daemon=True).start()
            else:
                silence_counter = 0

    print("=== Голосовой ввод (авто) ===")
    print("Просто говори — текст появится автоматически")
    print("Нажми ESC для выхода\n", flush=True)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        blocksize=CHUNK_SIZE, callback=callback):
        keyboard.wait("esc")

    print("\nВыход.")


if __name__ == "__main__":
    if not DEEPGRAM_API_KEY:
        print("ОШИБКА: не найден DEEPGRAM_API_KEY в .env")
        input()
    else:
        run()
