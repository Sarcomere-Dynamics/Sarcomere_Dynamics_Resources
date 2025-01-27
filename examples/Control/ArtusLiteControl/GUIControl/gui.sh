#!/bin/bash

gnome-terminal -- python3 ../../Tracking/gui_data/artus_lite_gui_publisher.py
sleep 5
gnome-terminal -- python3 gui_controller.py