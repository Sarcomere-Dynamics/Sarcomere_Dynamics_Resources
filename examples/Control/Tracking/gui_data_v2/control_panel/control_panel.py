"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""
import os
import json
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg



class ControlPanelWidget(QtWidgets.QWidget):
    def __init__(self, slider_control=None, win=None, hand_poses_directory="//"):
        super().__init__()

        self.hand_poses_directory = hand_poses_directory

        self.slider_control = slider_control  # Pass slider control to interact with the sliders
        
        # Store velocities per joint (preserved from loaded files)
        # Maps: {"thumb_spread": 50, "thumb_flex": 50, ...}
        # Default velocity used when no velocity was previously loaded
        self.default_velocity = 50
        self.joint_velocities = {}
        
        # self.layout = QtWidgets.QVBoxLayout() # for vertical layout
        self.layout = QtWidgets.QHBoxLayout()  # for horizontal layout

        if win is not None:
            self.win = win
        else:
            self.win = pg.GraphicsLayoutWidget(show=True)

        # Stream Button
        self.streaming = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stream_data)
        self.stream_button = QtWidgets.QPushButton('Stream')
        self.stream_button.clicked.connect(self.toggle_stream)
        self.stream_button.setStyleSheet('color: red;')  # Change button color
        self.layout.addWidget(self.stream_button, 0, QtCore.Qt.AlignTop)

        # Send Button
        self.send_button = QtWidgets.QPushButton('Send')
        self.send_button.clicked.connect(self.send_data)
        self.layout.addWidget(self.send_button, 0, QtCore.Qt.AlignTop)

        # Save Button and Filename Input
        self.save_button = QtWidgets.QPushButton('Save')
        self.save_filename_input = QtWidgets.QLineEdit(self)
        self.save_filename_input.setPlaceholderText('Enter filename')

        # Prevent stretching by setting maximum width for the filename input
        self.save_filename_input.setMaximumWidth(250)  # Limit the width
        self.save_filename_input.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.save_button.clicked.connect(self.save_data)
        self.layout.addWidget(self.save_filename_input, 0, QtCore.Qt.AlignTop)
        self.layout.addWidget(self.save_button, 0, QtCore.Qt.AlignTop)

        # Load Button and Dropdown
        self.load_button = QtWidgets.QPushButton('Load')
        self.file_selector = QtWidgets.QComboBox(self)
        self.load_button.clicked.connect(self.load_data)
        self.layout.addWidget(self.file_selector, 0, QtCore.Qt.AlignTop)
        self.layout.addWidget(self.load_button, 0, QtCore.Qt.AlignTop)

        # Set Speed Button and Speed Input
        # self.speed_input = QtWidgets.QLineEdit(self)
        # self.speed_input.setPlaceholderText('Enter speed')
        # self.speed_input.setMaximumWidth(100)  # Limit the width
        # self.speed_input.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # self.layout.addWidget(self.speed_input, 0, QtCore.Qt.AlignTop)
        # self.set_speed_button = QtWidgets.QPushButton('Set Speed')
        # self.layout.addWidget(self.set_speed_button, 0, QtCore.Qt.AlignTop)
        
        self.update_file_selector()  # Update the dropdown with available files
        # Set the layout for the control panel
        self.setLayout(self.layout)

    def toggle_stream(self):
        # Start or stop streaming based on the current state
        print("Toggling stream")  # Placeholder for the stream functionality
        if self.streaming:
            self.stream_button.setStyleSheet('color: red;')
            self.timer.stop()
            self.streaming = False
        else:
            self.stream_button.setStyleSheet('color: green;')
            self.timer.start(20) # Stream every 20 ms
            self.streaming = True

    def stream_data(self):
        # print("Streaming data")  # Placeholder for the stream functionality
        print("Streaming data")
        # Get current slider values and stream them (e.g., to a server or display)
        self.send_data()

    def send_data(self):
        # Get current slider values and send them (e.g., to a server or display)
        data = self.slider_control.get_joint_values()
        print(f"Sending data: {data}")

    def save_data(self):
        # Save the current slider values to a file in grasp format
        filename = self.save_filename_input.text()
        if not filename:
            print("Please enter a filename.")
            return

        # Map from internal slider keys to grasp format
        internal_to_grasp = {
            "Thumb_1": "thumb_spread", "Thumb_2": "thumb_flex", "Thumb_3": "thumb_d2", "Thumb_4": "thumb_d1",
            "Index_1": "index_spread", "Index_2": "index_flex", "Index_3": "index_d2",
            "Middle_1": "middle_spread", "Middle_2": "middle_flex", "Middle_3": "middle_d2",
            "Ring_1": "ring_spread", "Ring_2": "ring_flex", "Ring_3": "ring_d2",
            "Pinky_1": "pinky_spread", "Pinky_2": "pinky_flex", "Pinky_3": "pinky_d2"
        }
        
        # Joint index mapping (0-15)
        joint_index = {
            "thumb_spread": 0, "thumb_flex": 1, "thumb_d2": 2, "thumb_d1": 3,
            "index_spread": 4, "index_flex": 5, "index_d2": 6,
            "middle_spread": 7, "middle_flex": 8, "middle_d2": 9,
            "ring_spread": 10, "ring_flex": 11, "ring_d2": 12,
            "pinky_spread": 13, "pinky_flex": 14, "pinky_d2": 15
        }
        
        # Collect data directly from sliders in grasp format
        # Use stored velocities if available, otherwise use default
        grasp_data = {}
        
        for internal_key, grasp_key in internal_to_grasp.items():
            if internal_key in self.slider_control.sliders:
                angle = self.slider_control.sliders[internal_key].value()
                # Use stored velocity if available, otherwise default
                velocity = self.joint_velocities.get(grasp_key, self.default_velocity)
                grasp_data[grasp_key] = {
                    "target_angle": angle,
                    "velocity": velocity,
                    "index": joint_index[grasp_key]
                }
        
        # Save it in the hand_poses_directory
        file_path = os.path.join(self.hand_poses_directory, f"{filename}.json")

        with open(file_path, 'w') as f:
            json.dump(grasp_data, f, indent=4)

        print(f"Saved data to {file_path}")
        self.update_file_selector()

    def load_data(self):
        # Load data from the selected file in the dropdown
        filename = self.file_selector.currentText()
        if filename:
            file_path = os.path.join(self.hand_poses_directory, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                print(f"Loaded data from {file_path}: {data}")
                
                # Map from grasp format back to internal slider keys
                grasp_to_internal = {
                    "thumb_spread": "Thumb_1", "thumb_flex": "Thumb_2", "thumb_d2": "Thumb_3", "thumb_d1": "Thumb_4",
                    "index_spread": "Index_1", "index_flex": "Index_2", "index_d2": "Index_3",
                    "middle_spread": "Middle_1", "middle_flex": "Middle_2", "middle_d2": "Middle_3",
                    "ring_spread": "Ring_1", "ring_flex": "Ring_2", "ring_d2": "Ring_3",
                    "pinky_spread": "Pinky_1", "pinky_flex": "Pinky_2", "pinky_d2": "Pinky_3"
                }
                
                # Check if this is the new grasp format (nested objects) or old format (flat dict)
                first_value = list(data.values())[0] if data else None
                is_grasp_format = isinstance(first_value, dict) and ("target_angle" in first_value or "input_angle" in first_value)
                
                # Clear existing velocities before loading new ones
                if is_grasp_format:
                    self.joint_velocities.clear()
                
                # Update sliders with the loaded data and preserve velocities
                for key, value in data.items():
                    if is_grasp_format:
                        # New grasp format: extract angle and velocity from nested object
                        if isinstance(value, dict):
                            angle = value.get("target_angle") or value.get("input_angle", 0)
                            # Store velocity from file (supports both "velocity" and "input_speed")
                            velocity = value.get("velocity") or value.get("input_speed")
                            if velocity is not None:
                                # Store velocity for this joint (using grasp format key)
                                self.joint_velocities[key] = velocity
                            internal_key = grasp_to_internal.get(key)
                        else:
                            continue
                    else:
                        # Old format: direct value, key is already internal format
                        # No velocity information in old format, keep existing or use default
                        angle = value
                        internal_key = key
                    
                    if internal_key and internal_key in self.slider_control.sliders:
                        self.slider_control.sliders[internal_key].setValue(angle)
                        # Explicitly update the joint_values dictionary
                        self.slider_control.joint_values[internal_key] = angle
                    elif internal_key:
                        print(f"Warning: Slider key {internal_key} not found.")
        else:
            print("Please select a file to load.")

    def update_file_selector(self):
        # Update the dropdown with available files in the hand_poses_directory
        if not os.path.exists(self.hand_poses_directory):
            print(f"Directory {self.hand_poses_directory} does not exist.")
            return

        files = [f for f in os.listdir(self.hand_poses_directory) if f.endswith('.json')]
        self.file_selector.clear()
        self.file_selector.addItems(files)



def main():
    app = QtWidgets.QApplication([])

    # Create a GraphicsLayoutWidget for the control window
    win = pg.GraphicsLayoutWidget(show=True)

    # Create a SliderControl instance
    import os
    import sys
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("PROJECT_ROOT: ", PROJECT_ROOT)
    sys.path.append(PROJECT_ROOT)
    from gui.sliders_commands.slider_class import SliderControl
    # Create a SliderControl instance
    slider_control = SliderControl(rows=5, cols=4, win=win)

    # Create a ControlPanelWidget instance
    control_panel = ControlPanelWidget(slider_control, win=win)

    # Add the control panel to the layout
    win.addItem(control_panel)

    app.exec_()


if __name__ == '__main__':
    main()
