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
from PySide6 import QtCore, QtGui, QtWidgets
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

# dependencies
from examples.Tracking.zmq_class.zmq_class import ZMQPublisher
from examples.config.configuration import ArtusConfig
from ArtusAPI.robot.robot import Robot

class UIControl(QtWidgets.QWidget, ZMQPublisher):
    """
    This class is used to show the control elements in the UI for the robot
    This includes:
    * sliders and entry box for setting the joint angles
    * buttons for sending the joint angles to the robot
    * button for saving the joint angles to a file
    * button for to continuously send the joint angles to the robot
    ZMQPublisher is used on the backend to send the joint angles to the robot
    """
    def __init__(self, win=None, zmq_sliderCommands_pubPort=5556):
        QtWidgets.QWidget.__init__(self)
        ZMQPublisher.__init__(self, address=f"tcp://127.0.0.1:{zmq_sliderCommands_pubPort}")
        robot = None
        if ArtusConfig().config.robots.left_hand_robot.robot_connected:
            robot = ArtusConfig().config.robots.left_hand_robot.robot_type
        elif ArtusConfig().config.robots.right_hand_robot.robot_connected:
            robot = ArtusConfig().config.robots.right_hand_robot.robot_type
        else:
            raise ValueError("No robot connected")
        self.win = win

        self.joint_names = list(Robot(robot_type=robot).robot.hand_joints.keys())
        self.minimum_angle = {name: Robot(robot_type=robot).robot.hand_joints[name].min_angle for name in self.joint_names}
        self.maximum_angle = {name: Robot(robot_type=robot).robot.hand_joints[name].max_angle for name in self.joint_names}
        self.joint_values = {name: 0.0 for name in self.joint_names}  # Initialize joint values
        self.sliders = {}
        self.line_edit = {}
        self.streaming = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stream_data)

        self._init_ui()

    def _init_ui(self):
        self.layout = QtWidgets.QVBoxLayout()

        # Joint control group
        joint_control_group = QtWidgets.QGroupBox("Joint Control")
        joint_control_layout = QtWidgets.QGridLayout()

        for i, name in enumerate(self.joint_names):
            label = QtWidgets.QLabel(name)
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(self.minimum_angle[name], self.maximum_angle[name])  # Example range, adjust as needed
            slider.setValue(0)
            slider.setTickInterval(10)
            slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            slider.setSingleStep(1)
            slider.valueChanged.connect(lambda value, n=name: self.update_joint_angle(n, value))

            line_edit = QtWidgets.QLineEdit("0.0")
            line_edit.setValidator(QtGui.QDoubleValidator())
            line_edit.setMaximumWidth(60)
            line_edit.textChanged.connect(lambda text, n=name: self.update_joint_angle_from_text(n, text))

            self.sliders[name] = slider
            self.line_edit[name] = line_edit

            joint_control_layout.addWidget(label, i, 0)
            joint_control_layout.addWidget(slider, i, 1)
            joint_control_layout.addWidget(line_edit, i, 2)

        joint_control_group.setLayout(joint_control_layout)
        self.layout.addWidget(joint_control_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.send_button = QtWidgets.QPushButton("Send Angles")
        self.send_button.clicked.connect(self.send_data)
        button_layout.addWidget(self.send_button)

        self.save_button = QtWidgets.QPushButton("Save Angles")
        self.save_button.clicked.connect(self.save_data)
        button_layout.addWidget(self.save_button)

        self.stream_button = QtWidgets.QPushButton("Start Stream")
        self.stream_button.clicked.connect(self.toggle_stream)
        button_layout.addWidget(self.stream_button)

        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

    def update_joint_angle(self, name, value):
        self.joint_values[name] = float(value)
        self.line_edit[name].setText(str(float(value)))

    def update_joint_angle_from_text(self, name, text):
        try:
            value = float(text)
            self.joint_values[name] = value
            self.sliders[name].setValue(int(value))
        except ValueError:
            pass # Handle invalid text input

    def send_data(self):
        # This will send the current joint values via ZMQ
        print(f"Sending data to ZMQ")
        self.send(topic="Target", message=json.dumps(self.joint_values))

    def save_data(self):
        # Placeholder for saving joint angles to a file
        print(f"Saving data: {self.joint_values}")
        # Here you would implement the file saving logic, similar to control_panel.py
        # For example:
        # with open("joint_angles.json", "w") as f:
        #     json.dump(self.joint_values, f)

    def toggle_stream(self):
        if self.streaming:
            self.timer.stop()
            self.streaming = False
            self.stream_button.setText("Start Stream")
            self.stream_button.setStyleSheet("")
        else:
            self.timer.start(50)  # Stream every 50 ms
            self.streaming = True
            self.stream_button.setText("Stop Stream")
            self.stream_button.setStyleSheet("background-color: red")

    def stream_data(self):
        self.send_data()


def main():
    app = QtWidgets.QApplication(sys.argv)
    ui_control_window = UIControl()
    ui_control_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
