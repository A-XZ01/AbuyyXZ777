@echo off
title ASBLOX Discord Bot
color 0A
echo ========================================
echo    ASBLOX Discord Bot Launcher
echo ========================================
echo.
echo [*] Starting bot...
echo.
cd /d "%~dp0"
python bot.py
echo.
echo ========================================
echo    Bot stopped!
echo ========================================
echo.
pause
