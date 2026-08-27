@echo off
REM FRIDAY Launcher - activates venv and starts assistant
cd /d "D:\FRIDAY\FRIDAY"
call "D:\FRIDAY\FRIDAY\venv\Scripts\activate.bat"
python main.py %*
