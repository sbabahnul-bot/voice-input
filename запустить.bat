@echo off
chcp 65001 > nul
title Голосовой ввод
cd /d "%~dp0"
"C:\Users\Sergey_B\AppData\Local\Programs\Python\Python312\python.exe" voice_input.py
pause
