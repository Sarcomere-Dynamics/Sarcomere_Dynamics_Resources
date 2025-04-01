#!/bin/bash

# Add variable for python path
PYTHON_PATH="/home/general/Desktop/github_files/Sarcomere_Dynamics_Resources/examples/venv/bin/python"

# Launch first terminal and run the first script
gnome-terminal -- bash -c "$PYTHON_PATH ../../Tracking/gui_data_v2/artus_lite_gui.py; echo 'Press Enter to close...'; read"

# Wait for 5 seconds before launching the next terminal
sleep 5

# Launch second terminal and run the second script
gnome-terminal -- bash -c "$PYTHON_PATH gui_controller.py; echo 'Press Enter to close...'; read"
