@echo off
cd /d "%~dp0"
start "" python3  ..\..\Tracking\gui_data\artus_lite_gui_publisher.py
timeout /t 5 /nobreak
python3 .\gui_controller.py