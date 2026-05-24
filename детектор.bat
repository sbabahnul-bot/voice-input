@echo off
chcp 65001 > nul
"C:\Users\Sergey_B\AppData\Local\Programs\Python\Python312\python.exe" -c "import keyboard; print('Нажимай клавиши - покажу названия. Ctrl+C выход.'); keyboard.hook(lambda e: print(e.event_type, e.name, flush=True) if e.event_type=='down' else None); keyboard.wait('ctrl+c')"
pause
