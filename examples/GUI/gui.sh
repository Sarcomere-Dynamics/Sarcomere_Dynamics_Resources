#!/bin/bash

# Add variable for python path
# PYTHON_PATH="/home/general/Desktop/github_files/Sarcomere_Dynamics_Resources/examples/venv/bin/python"

# get cwd
CWD=$(pwd)

# exit if the cwd is not GUI folder by checking the last folder name
if [ $(basename $CWD) != "GUI" ]; then
    echo "Error: Not in GUI folder"
    exit 1
fi

# Launch first terminal and run the first script
gnome-terminal -- bash -c "python3 ../Tracking/ui/ui.py; echo 'Press Enter to close...'; read"

# Wait for 5 seconds before launching the next terminal
sleep 5

# Launch second terminal and run the second script
gnome-terminal -- bash -c "python3 gui_controller.py; echo 'Press Enter to close...'; read"