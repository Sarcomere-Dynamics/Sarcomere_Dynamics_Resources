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
        self.force_value = 10.0
        self.speed_value = 150.0
        self.minimum_force = Robot(robot_type=robot).robot.min_force
        self.minimum_speed = Robot(robot_type=robot).robot.min_velocity
        self.maximum_force = Robot(robot_type=robot).robot.max_force
        self.maximum_speed = Robot(robot_type=robot).robot.max_velocity
        self.sliders = {}
        self.line_edit = {}
        self.streaming = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stream_data)

        self._init_ui()
        self.populate_load_dropdown()

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

        # Force and Speed control group
        force_speed_control_group = QtWidgets.QGroupBox("Force and Speed Control")
        force_speed_control_layout = QtWidgets.QGridLayout()

        # Force Slider
        force_label = QtWidgets.QLabel("Force (N)")
        self.force_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.force_slider.setRange(self.minimum_force, self.maximum_force)
        self.force_slider.setValue(int(self.force_value))
        self.force_slider.setTickInterval(5)
        self.force_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.force_slider.setSingleStep(1)
        self.force_slider.valueChanged.connect(self.update_force)

        self.force_line_edit = QtWidgets.QLineEdit(str(self.force_value))
        self.force_line_edit.setValidator(QtGui.QDoubleValidator())
        self.force_line_edit.setMaximumWidth(60)
        self.force_line_edit.textChanged.connect(self.update_force_from_text)

        force_speed_control_layout.addWidget(force_label, 0, 0)
        force_speed_control_layout.addWidget(self.force_slider, 0, 1)
        force_speed_control_layout.addWidget(self.force_line_edit, 0, 2)

        # Speed Slider
        speed_label = QtWidgets.QLabel("Speed (deg/s)")
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(self.minimum_speed, self.maximum_speed)
        self.speed_slider.setValue(int(self.speed_value))
        self.speed_slider.setTickInterval(50)
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.valueChanged.connect(self.update_speed)

        self.speed_line_edit = QtWidgets.QLineEdit(str(self.speed_value))
        self.speed_line_edit.setValidator(QtGui.QDoubleValidator())
        self.speed_line_edit.setMaximumWidth(60)
        self.speed_line_edit.textChanged.connect(self.update_speed_from_text)

        force_speed_control_layout.addWidget(speed_label, 1, 0)
        force_speed_control_layout.addWidget(self.speed_slider, 1, 1)
        force_speed_control_layout.addWidget(self.speed_line_edit, 1, 2)

        force_speed_control_group.setLayout(force_speed_control_layout)
        self.layout.addWidget(force_speed_control_group)

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

        # Load control group
        load_control_group = QtWidgets.QGroupBox("Load Joint Angles")
        load_control_layout = QtWidgets.QHBoxLayout()

        self.load_dropdown = QtWidgets.QComboBox()
        load_control_layout.addWidget(self.load_dropdown)

        self.load_button = QtWidgets.QPushButton("Load Angles")
        self.load_button.clicked.connect(self.load_data)
        load_control_layout.addWidget(self.load_button)

        load_control_group.setLayout(load_control_layout)
        self.layout.addWidget(load_control_group)

        self.setLayout(self.layout)

    def update_joint_angle(self, name, value):
        self.joint_values[name] = float(value)
        self.line_edit[name].setText(str(float(value)))
        self.sliders[name].setValue(int(value))

    def update_force(self, value):
        self.force_value = float(value)
        self.force_line_edit.setText(str(float(value)))
        self.force_slider.setValue(int(value))

    def update_speed(self, value):
        self.speed_value = float(value)
        self.speed_line_edit.setText(str(float(value)))
        self.speed_slider.setValue(int(value))

    def update_joint_angle_from_text(self, name, text):
        try:
            value = float(text)
            self.joint_values[name] = value
            self.sliders[name].setValue(int(value))
        except ValueError:
            pass # Handle invalid text input

    def update_force_from_text(self, text):
        try:
            value = float(text)
            self.force_value = value
            self.force_slider.setValue(int(value))
        except ValueError:
            pass # Handle invalid text input
    
    def update_speed_from_text(self, text):
        try:
            value = float(text)
            self.speed_value = value
            self.speed_slider.setValue(int(value))
        except ValueError:
            pass # Handle invalid text input

    def send_data(self):
        # This will send the current joint values via ZMQ
        print(f"Sending data to ZMQ")
        data_to_send = {
            "joint_values": self.joint_values,
            "force": self.force_value,
            "speed": self.speed_value
        }
        self.send(topic="Target", message=json.dumps(data_to_send))

    def save_data(self):
        # Get filename from user using a QInputDialog
        filename, ok = QtWidgets.QInputDialog.getText(self, "Save Joint Angles", "Enter filename (e.g., my_pose.json):")
        if ok and filename:
            # Ensure the filename has a .json extension
            if not filename.endswith(".json"):
                filename += ".json"
            
            # Define the directory to save the poses
            save_directory = os.path.join(PROJECT_ROOT, "data", "hand_poses")
            # os.makedirs(save_directory, exist_ok=True) # Create directory if it doesn't exist

            # convert the joint values to the loaded values format which is key: {'target_angle': int(value)}
            loaded_values = {key: {'target_angle': int(value)} for key,value in self.joint_values.items()}

            filepath = os.path.join(save_directory, filename)
            try:
                with open(filepath, "w") as f:
                    json.dump(loaded_values, f, indent=4)
                print(f"Joint angles saved to {filepath}")
                self.populate_load_dropdown()
            except Exception as e:
                print(f"Error saving data: {e}")
        else:
            print("Save operation cancelled or no filename entered.")

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


    def populate_load_dropdown(self):
        save_directory = os.path.join(PROJECT_ROOT, "data", "hand_poses")
        os.makedirs(save_directory, exist_ok=True) # Ensure the directory exists
        self.load_dropdown.clear()
        files = [f for f in os.listdir(save_directory) if f.endswith(".json")]
        self.load_dropdown.addItems(sorted(files))

    def load_data(self):
        selected_file = self.load_dropdown.currentText()
        if selected_file:
            filepath = os.path.join(PROJECT_ROOT, "data", "hand_poses", selected_file)
            try:
                with open(filepath, "r") as f:
                    loaded_values = json.load(f)

                # I want to convert the loaded values to the joint values format which is key: float value
                loaded_values = {key: value['target_angle'] for key,value in loaded_values.items()}
                
                for name, value in loaded_values.items():
                    if name in self.joint_names:
                        self.update_joint_angle(name, value)
                print(f"Loaded joint angles from {filepath}")
            except Exception as e:
                print(f"Error loading data: {e}")
        else:
            print("No file selected to load.")


def main():
    app = QtWidgets.QApplication(sys.argv)
    ui_control_window = UIControl()
    ui_control_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
