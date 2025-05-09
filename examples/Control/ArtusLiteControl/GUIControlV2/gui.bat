@echo off
REM Set variable for python path (update the path accordingly)
@REM set PYTHON_PATH="C:\path\to\your\venv\Scripts\python.exe"
PYTHON_PATH="python"

REM Launch first terminal and run the first script
start "Artus Lite GUI" cmd /k "%PYTHON_PATH% ..\..\Tracking\gui_data_v2\artus_lite_gui.py & echo Press Enter to close... & pause"

REM Wait for 5 seconds before launching the next terminal
timeout /t 5

REM Launch second terminal and run the second script
start "GUI Controller" cmd /k "%PYTHON_PATH% gui_controller.py & echo Press Enter to close... & pause"