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
import sys
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

# dependencies
from examples.Tracking.zmq_class.zmq_class import ZMQSubscriber
from examples.config.configuration import ArtusConfig
from ArtusAPI.robot.robot import Robot

class UIFeedback(QtWidgets.QWidget, ZMQSubscriber):
    def __init__(self, win=None, zmq_feedback_subPort="tcp://127.0.0.1:5555"):
        QtWidgets.QWidget.__init__(self)
        ZMQSubscriber.__init__(self, address=zmq_feedback_subPort, topics=["Feedback"])
        robot = None
        if ArtusConfig().config.robots.left_hand_robot.robot_connected:
            robot = ArtusConfig().config.robots.left_hand_robot.robot_type
        elif ArtusConfig().config.robots.right_hand_robot.robot_connected:
            robot = ArtusConfig().config.robots.right_hand_robot.robot_type
        else:
            raise ValueError("No robot connected")

        # Cache robot description to discover joints and any force sensors
        self.robot_description = Robot(robot_type=robot).robot
        # self.minimum_force = Robot(robot_type=robot).robot.min_force
        # self.minimum_speed = Robot(robot_type=robot).robot.min_velocity
        # self.maximum_force = Robot(robot_type=robot).robot.max_force
        # self.maximum_speed = Robot(robot_type=robot).robot.max_velocity

        self.win = win
        self.feedback_type = "angle"  # Default feedback type
        self.feedback_types = ["angle", "velocity", "force"]

        self.joint_names = list(self.robot_description.hand_joints.keys())
        self.plots = []
        self.curves = []
        self.data = []
        self.ptr = []

        self.force_sensor_info = getattr(self.robot_description, "force_sensors", None)
        self.force_sensor_names = list(self.force_sensor_info.keys()) if self.force_sensor_info else []
        self.force_sensor_axes = ["x", "y", "z"]
        self.force_plots = {}
        self.force_curves = {}
        self.force_data = {}
        self.force_ptr = {}

        self.history_length = 500  # Number of data points to display

        self._init_ui()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # Update every 50 ms

    def _init_ui(self):
        self.layout = QtWidgets.QVBoxLayout()

        # Feedback type dropdown
        feedback_type_layout = QtWidgets.QHBoxLayout()
        feedback_type_label = QtWidgets.QLabel("Feedback Type:")
        self.feedback_type_selector = QtWidgets.QComboBox(self)
        self.feedback_type_selector.addItems(["angle", "velocity", "force"])
        self.feedback_type_selector.setCurrentText(self.feedback_type)
        self.feedback_type_selector.currentIndexChanged.connect(self._on_feedback_type_changed)
        feedback_type_layout.addWidget(feedback_type_label)
        feedback_type_layout.addWidget(self.feedback_type_selector)
        self.layout.addLayout(feedback_type_layout)

        self.plot_widget = pg.GraphicsLayoutWidget(show=True)
        self.plot_widget.setWindowTitle('Artus Lite Feedback Visualization')
        self.layout.addWidget(self.plot_widget)

        self.create_joint_plots()
        if self.force_sensor_names:
            self.create_force_sensor_plots()
        self.setLayout(self.layout)

    def create_joint_plots(self):
        num_cols = np.ceil(len(self.joint_names) / 2)  # Number of plots per row
        self.plot_widget.nextRow()
        for i, name in enumerate(self.joint_names):
            plot_item = self.plot_widget.addPlot(title=name)
            plot_item.setYRange(-90, 90)  # Adjust range as needed
            curve = plot_item.plot(pen='g') # Default to green for angle

            self.plots.append(plot_item)
            self.curves.append(curve)
            self.data.append(np.zeros(self.history_length))
            self.ptr.append(0)

            if (i + 1) % num_cols == 0:
                self.plot_widget.nextRow()

    def create_force_sensor_plots(self):
        """
        Create plots for any available force sensors (Talos).
        Each force sensor gets a plot with X/Y/Z curves.
        """
        if not self.force_sensor_names:
            return

        axis_colors = {"x": "r", "y": "g", "z": "b"}
        self.plot_widget.nextRow()
        num_cols = np.ceil(len(self.joint_names) / 2)  # Number of plots per row
        for i, sensor_name in enumerate(self.force_sensor_names):
            plot_item = self.plot_widget.addPlot(title=f"{sensor_name} force (N)")
            plot_item.setYRange(-5, 5)
            self.force_plots[sensor_name] = plot_item
            self.force_curves[sensor_name] = {}
            self.force_data[sensor_name] = {}
            self.force_ptr[sensor_name] = 0

            for axis in self.force_sensor_axes:
                self.force_curves[sensor_name][axis] = plot_item.plot(pen=axis_colors[axis])
                self.force_data[sensor_name][axis] = np.zeros(self.history_length)

            if (i + 1) % num_cols == 0:
                self.plot_widget.nextRow()

    def update_plots(self):
        raw_data = self.receive()
        if raw_data is None:
            # print(f"No feedback data received from ZMQ Subscriber")
            return

        # print(f"Feedback data received from ZMQ")

        try:
            feedback_data = json.loads(raw_data)
            # Assuming feedback_data is a dictionary where keys are joint names
            # and values are the feedback values
            for i, name in enumerate(self.joint_names):
                if name in feedback_data:
                    value = feedback_data[name][f'feedback_{self.feedback_type}']
                    self.data[i][:-1] = self.data[i][1:]
                    self.data[i][-1] = value
                    self.curves[i].setData(self.data[i])
                    self.curves[i].setPos(self.ptr[i], 0)
                    self.ptr[i] += 1

            # Update force sensor plots if available
            if self.force_sensor_names and 'force_sensors' in feedback_data:
                sensor_feedback = feedback_data.get('force_sensors', {})
                for sensor_name in self.force_sensor_names:
                    axis_data = sensor_feedback.get(sensor_name)
                    if not axis_data:
                        continue
                    for axis in self.force_sensor_axes:
                        value = axis_data.get(axis, 0)
                        self.force_data[sensor_name][axis][:-1] = self.force_data[sensor_name][axis][1:]
                        self.force_data[sensor_name][axis][-1] = value
                        self.force_curves[sensor_name][axis].setData(self.force_data[sensor_name][axis])
                        self.force_curves[sensor_name][axis].setPos(self.force_ptr[sensor_name], 0)
                    self.force_ptr[sensor_name] += 1
        except json.JSONDecodeError:
            print("Error decoding JSON feedback data.")

        print(f"Updated Plots")

    def _on_feedback_type_changed(self):
        self.feedback_type = self.feedback_type_selector.currentText()
        print(f"Feedback type changed to: {self.feedback_type}")
        self.reset_plots()

    def reset_plots(self):
        for i, plot_item in enumerate(self.plots):
            # Clear existing data
            self.data[i] = np.zeros(self.history_length)
            self.ptr[i] = 0
            self.curves[i].setData(self.data[i])
            self.curves[i].setPos(self.ptr[i], 0)

            # Set y-range and color based on feedback type
            if self.feedback_type == "force":
                plot_item.setYRange(-self.robot_description.max_force, self.robot_description.max_force)
                self.curves[i].setPen('r')
            elif self.feedback_type == "velocity":
                plot_item.setYRange(-self.robot_description.max_velocity, self.robot_description.max_velocity)  # Keep current range
                self.curves[i].setPen('y')
            elif self.feedback_type == "angle":
                plot_item.setYRange(-90, 90)  # Keep current range
                self.curves[i].setPen('g')

        # Reset force sensor plot data
        for sensor_name in self.force_sensor_names:
            for axis in self.force_sensor_axes:
                self.force_data[sensor_name][axis] = np.zeros(self.history_length)
                self.force_curves[sensor_name][axis].setData(self.force_data[sensor_name][axis])
                self.force_curves[sensor_name][axis].setPos(0, 0)
            self.force_ptr[sensor_name] = 0


def main():
    app = QtWidgets.QApplication(sys.argv)
    ui_feedback_window = UIFeedback()
    ui_feedback_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
