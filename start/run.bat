@echo off
cd /d "%~dp0"
cd ..
call .venv\Scripts\activate
python src\main_gui.py
pause
