@echo off
setlocal

:: Step 4: Launch the Game
cd sources
echo Launching the game...
"../PythonEmbedded/python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to launch the game.
    pause
    exit /B 1
)

pause
