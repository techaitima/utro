@echo off
echo ========================================
echo Starting Utro Bot v2
echo ========================================

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using system Python
)

REM Run the bot
echo Starting bot...
python bot_v2.py

pause
