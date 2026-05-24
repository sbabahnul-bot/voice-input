@echo off
chcp 65001 > nul
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
echo Нажми F9 (любую клавишу) - должно появиться сообщение
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -c "
import keyboard
print('Жду F9...')
keyboard.wait('f9')
print('F9 нажата! Всё работает.')
input('Нажми Enter для выхода')
"
pause
