"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import sys
import os
import json

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QGridLayout,
                             QGroupBox, QPushButton, QComboBox, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtCore import Qt, QTimer

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

class ArtusControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        # directory path to save the joint positions
        self.directory = str(PROJECT_ROOT) + "//Sarcomere_Dynamics_Resources//examples//Control//ArtusLiteControl//GUIControl//hand_pose_data//"

        self.joint_values = {}
        self.sliders = {}
        self.streaming = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.stream_joint_positions)
        self.initUI()

        # Setup ZMQ Publisher
        self._setup_zmq_publisher(address="tcp://127.0.0.1:5556")



    def _setup_zmq_publisher(self, address="tcp://127.0.0.1:5556"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQPublisher
        self.zmq_publisher = ZMQPublisher(address=address)



    def initUI(self):
        main_layout = QVBoxLayout()

        # Add buttons for Stream, Send, Save, and Load
        button_layout = QHBoxLayout()
        self.stream_button = QPushButton('Stream')
        self.stream_button.clicked.connect(self.toggle_stream)
        self.stream_button.setStyleSheet('color: red;')
        send_button = QPushButton('Send')
        send_button.clicked.connect(self._send_joint_angles)
        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_joint_positions)
        load_button = QPushButton('Load')
        load_button.clicked.connect(self.load_joint_positions)
        self.file_selector = QComboBox()
        self.update_file_selector()

        self.save_filename_input = QLineEdit(self)
        self.save_filename_input.setPlaceholderText('Enter filename')

        button_layout.addWidget(self.stream_button)
        button_layout.addWidget(send_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(self.file_selector)
        button_layout.addWidget(self.save_filename_input)

        main_layout.addLayout(button_layout)

        grid_layout = QGridLayout()

        # Create sections for left and right hand and arm
        left_hand_section = self.create_hand_section('Left Hand')
        right_hand_section = self.create_hand_section('Right Hand')


        # Add sections to grid layout
        grid_layout.addWidget(left_hand_section, 0, 0)
        grid_layout.addWidget(right_hand_section, 0, 1)

        main_layout.addLayout(grid_layout)
        self.setLayout(main_layout)
        self.setWindowTitle('ArtusLite Control GUI')
        self.setGeometry(100, 100, 800, 600)  # Set the initial size of the window
        self.show()

    def create_hand_section(self, title):
        group_box = QGroupBox(title)
        layout = QVBoxLayout()

        # Create and style title label
        title_label = self.create_label(title, QColor('black'), bold=True, size=14)
        layout.addWidget(title_label)

        # Define colors
        colors = {
            'thumb': QColor('violet'),
            'index': QColor('blue'),
            'middle': QColor('green'),
            'ring': QColor('red'),
            'pinky': QColor('orange')
        }

        # Thumb joints (4)
        thumb_layout = QVBoxLayout()
        thumb_layout.addWidget(self.create_label('Thumb', colors['thumb'], bold=True))
        for i in range(1, 5):
            min_val, max_val = (-25, 25) if i == 1 else (0, 90)
            thumb_layout.addWidget(self.create_label(f'Joint {i}', colors['thumb']))
            thumb_layout.addLayout(self.create_slider_with_value(min_val, max_val, f'{title.lower()}_thumb', i))

        layout.addLayout(thumb_layout)

        # Fingers joints (3 each for 4 fingers)
        fingers_layout = QGridLayout()
        finger_names = ['Index', 'Middle', 'Ring', 'Pinky']
        for idx, finger in enumerate(finger_names):
            finger_layout = QVBoxLayout()
            finger_layout.addWidget(self.create_label(f'{finger} Finger', colors[finger.lower()], bold=True))
            for i in range(1, 4):
                min_val, max_val = (-15, 15) if i == 1 else (0, 90)
                finger_layout.addWidget(self.create_label(f'Joint {i}', colors[finger.lower()]))
                finger_layout.addLayout(self.create_slider_with_value(min_val, max_val, f'{title.lower()}_{finger.lower()}', i))
            fingers_layout.addLayout(finger_layout, 0, idx)

        layout.addLayout(fingers_layout)

        group_box.setLayout(layout)
        return group_box



    def create_slider_with_value(self, min_val, max_val, part, joint):
        layout = QVBoxLayout()
        
        slider_layout = QHBoxLayout()
        min_label = QLabel(f'{min_val}')
        min_label.setAlignment(Qt.AlignCenter)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setSingleStep(1)
        slider.setTickPosition(QSlider.NoTicks)
        slider.setValue(0)  # Set the initial value to 0
        slider.valueChanged.connect(lambda value: self.update_joint(part, joint, value))
        max_label = QLabel(f'{max_val}')
        max_label.setAlignment(Qt.AlignCenter)

        # value_label = QLabel(f'{min_val}')
        value_label = QLabel(f'0')
        value_label.setAlignment(Qt.AlignCenter)

        slider.valueChanged.connect(lambda value: value_label.setText(f'{value}'))

        # Store the slider reference
        self.sliders[f'{part}_{joint}'] = slider

        slider_layout.addWidget(min_label)
        slider_layout.addWidget(slider)
        slider_layout.addWidget(max_label)

        layout.addLayout(slider_layout)
        layout.addWidget(value_label)

        # Initialize the joint value to zero
        self.joint_values[f'{part}_{joint}'] = 0

        return layout

    def create_label(self, text, color, bold=False, size=10):
        label = QLabel(text)
        palette = label.palette()
        palette.setColor(QPalette.WindowText, color)
        label.setPalette(palette)
        font = label.font()
        font.setBold(bold)
        font.setPointSize(size)
        label.setFont(font)
        return label
    


    def update_joint(self, part, joint, value):
        # Update joint values
        self.joint_values[f'{part}_{joint}'] = value
        print(f'Updating {part} joint {joint} to {value} degrees')



    # ------------------- Publish Joint Positions -------------------
    def stream_joint_positions(self):
        if not self.streaming:
            return
        self._send_joint_angles()
    def _send_joint_angles(self):
        joint_angles_dict = self._get_joint_angles_from_UI()
        print("Sending joint angles:", joint_angles_dict)
        self.zmq_publisher.send(topic="GUI",
                                message=json.dumps(joint_angles_dict))
    def _get_joint_angles_from_UI(self):
        # Return the current joint angles, grouped by section
        left_hand = {k: v for k, v in self.joint_values.items() if k.startswith('left hand')}
        right_hand = {k: v for k, v in self.joint_values.items() if k.startswith('right hand')}

        return {
            'left_hand': left_hand,
            'right_hand': right_hand
        }
    def toggle_stream(self):
        # Start or stop streaming based on the current state
        if self.streaming:
            self.timer.stop()
            # self.stream_button.setText('Stream')
            self.stream_button.setStyleSheet('color: red;')
            self.streaming = False
        else:
            self.timer.start(20) # Stream every 1 ms
            # self.stream_button.setText('Stop Streaming')
            self.stream_button.setStyleSheet('color: green;')
            self.streaming = True


    # ----------------- Save and Load Joint Positions -----------------
    def save_joint_positions(self):
        # Save current joint positions to a specified file
        directory = self.directory
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filename = self.save_filename_input.text()
        if not filename:
            filename = "joint_positions"
        
        filepath = os.path.join(directory, f"{filename}.json")
        with open(filepath, 'w') as file:
            json.dump(self.joint_values, file)
        
        self.update_file_selector()
        print("Saved joint positions to", filepath)
    def load_joint_positions(self):
        # Load joint positions from selected file
        filename = self.file_selector.currentText()
        if filename:
            filepath = self.directory + filename
            with open(filepath, 'r') as file:
                loaded_values = json.load(file)
                for key, value in loaded_values.items():
                    self.joint_values[key] = value
                    part, joint = key.rsplit('_', 1)
                    self.update_joint(part, int(joint), value)
                    # Update the slider value
                    self.sliders[key].setValue(value)
            print("Loaded joint positions from", filename)

    def update_file_selector(self):
        # Update the file selector with available files
        directory = self.directory
        if not os.path.exists(directory):
            os.makedirs(directory)
        files = [f for f in os.listdir(directory) if f.endswith('.json')]
        self.file_selector.clear()
        self.file_selector.addItems(files)
    





if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ArtusControlGUI()
    sys.exit(app.exec_())

# "C:\Users\General User\AppData\Local\ov\pkg\isaac_sim-2022.2.1\python.bat" "C:\Users\General User\Desktop\github_files\Isaac_Sim_Work\GUI\hyperion_control_gui.py"