#!/bin/bash

# Launch the artus_lite_gui_publisher and wait for its terminal to close
gnome-terminal --wait -- python3 ../../Tracking/gui_data/artus_lite_gui_publisher.py &
# Launch the gui_controller and wait for its terminal to close
gnome-terminal --wait -- python3 gui_controller.py &
PID2=$!
wait $PID2