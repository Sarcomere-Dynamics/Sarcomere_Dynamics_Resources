#!/bin/bash

gnome-terminal -- bash -c "python ../../Tracking/gui_data_v2/artus_lite_gui.py; echo 'Press Enter to close...'; read"
sleep 5
gnome-terminal -- bash -c "python gui_controller.py; echo 'Press Enter to close...'; read"