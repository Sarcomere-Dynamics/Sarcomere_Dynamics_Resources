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
        # Save the current slider values to a file
        filename = self.save_filename_input.text()
        if not filename:
            print("Please enter a filename.")
            return

        data = self.slider_control.get_joint_values()  # Use joint values instead of slider values
        # Save it in the hand_poses_directory
        file_path = os.path.join(self.hand_poses_directory, f"{filename}.json")

        with open(file_path, 'w') as f:
            json.dump(data, f)

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
                # Update sliders with the loaded data
                for key, value in data.items():
                    if key in self.slider_control.sliders:
                        self.slider_control.sliders[key].setValue(value)
                        # Explicitly update the joint_values dictionary
                        self.slider_control.joint_values[key] = value
                    else:
                        print(f"Warning: Slider key {key} not found.")
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
