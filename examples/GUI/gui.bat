@echo off
@REM REM Set variable for python path (update the path accordingly)
set PYTHON_PATH=venv\Scripts\python.exe
@REM REM Launch first terminal and run the first script
start "Artus Lite GUI" cmd /k "%PYTHON_PATH% ../Tracking/ui/ui.py & echo Press Enter to close... & pause"
@REM REM Wait for 5 seconds before launching the next terminal
timeout /t 5
@REM REM Launch second terminal and run the second script
start "GUI Controller" cmd /k "%PYTHON_PATH% gui_controller.py & echo Press Enter to close... & pause"