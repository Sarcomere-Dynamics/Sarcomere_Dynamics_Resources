"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor
import numpy as np


class SliderControl:
    def __init__(self, rows=5, cols=4, win=None):
        self.rows = rows
        self.cols = cols
        self.sliders = {}  # Dictionary to store sliders
        self.slider_values = {}  # To store slider values
        self.app = QtWidgets.QApplication([])

        # Create a GraphicsLayoutWidget for the control window
        if win is not None:
            self.win = win
        else:
            self.win = pg.GraphicsLayoutWidget(show=True)
            # self.win.show()


        self.joint_values = {} # position commands

        self.finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        # Define colors
        self.colors = {
            "Thumb": QColor('violet'),
            "Index": QColor('blue'),
            "Middle": QColor('green'),
            "Ring": QColor('red'),
            "Pinky": QColor('orange')
        }

        self.min_max_values = {
            "Thumb": [(-35,35), (0, 90), (0, 90), (0, 90)],
            "Index": [(-15, 15), (0, 90), (0, 90)],
            "Middle": [(-15, 15), (0, 90), (0, 90)],
            "Ring": [(-15, 15), (0, 90), (0, 90)],
            "Pinky": [(-15, 15), (0, 90), (0, 90)]
        }


        # Create sliders and add them to the window
        # self._create_sliders() # not used
        self.create_joint_sliders()

    def create_joint_sliders(self, title="Joint Control Sliders"):
        group_box = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QHBoxLayout()

        # # Create and style the title label
        # title_label = self.create_label(title, size=16, alignment=QtCore.Qt.AlignCenter, color=QColor('black'), bold=True)
        # layout.addWidget(title_label)


        ########### finger Sliders ###########
        for k in range(5): # five sliders for each finger
            finger_layout = QtWidgets.QVBoxLayout() # Vertical layout for thumb sliders
            # add title
            finger_title = self.create_label(self.finger_names[k], size=14, alignment=QtCore.Qt.AlignCenter, color=self.colors[self.finger_names[k]], bold=True)
            finger_layout.addWidget(finger_title)
            # add sliders
            for i in range(1, 5): # four sliders for thumb
                if k != 0 and i == 4: # create only 3 sliders for other fingers
                    # add placeholders
                    finger_layout.addWidget(QtWidgets.QLabel())
                    finger_layout.addWidget(QtWidgets.QLabel())
                    break
                # create joint label
                joint_label = self.create_label(f"Joint {i}", size=12, alignment=QtCore.Qt.AlignCenter, color=self.colors[self.finger_names[k]], bold=False)
                finger_layout.addWidget(joint_label)
                # create slider
                slider = self.create_slider_with_value(title=self.finger_names[k], joint_number=i, value=0, min_value=self.min_max_values[self.finger_names[k]][i-1][0], max_value=self.min_max_values[self.finger_names[k]][i-1][1], tick_interval=10)
                finger_layout.addLayout(slider)
            layout.addLayout(finger_layout)
            # add horizontal blackline element to separate fingers
            if k != 4:
                line = QtWidgets.QFrame()
                line.setFrameShape(QtWidgets.QFrame.VLine)
                line.setFrameShadow(QtWidgets.QFrame.Sunken)
                layout.addWidget(line)

            # add finger layout to the window
            
        # Create a QWidget to hold the layout
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        # Wrap the QWidget in a QGraphicsProxyWidget
        proxy_widget = QtWidgets.QGraphicsProxyWidget()
        proxy_widget.setWidget(widget)

        # Add the proxy widget to the layout at the appropriate row and column
        self.win.addItem(proxy_widget, 0, 0)  # Correct method signature




    def create_label(self, text, size=12, alignment=QtCore.Qt.AlignLeft, color=QColor('black'), bold=False):
        label = QtWidgets.QLabel(text)
        font = QtGui.QFont()
        font.setPointSize(size)
        font.setBold(bold)
        label.setFont(font)
        label.setAlignment(alignment)
        label.setStyleSheet(f"color: {color.name()}")
        return label
    
    def create_slider_with_value(self, title, joint_number, value=0, min_value=0, max_value=100, tick_interval=10, row=0, col=0):
        layout = QtWidgets.QVBoxLayout() 

        slider_layout = QtWidgets.QHBoxLayout()

        min_label = self.create_label(str(min_value), size=10, alignment=QtCore.Qt.AlignLeft, color=QColor('black'), bold=False)
        max_label = self.create_label(str(max_value), size=10, alignment=QtCore.Qt.AlignRight, color=QColor('black'), bold=False)
        
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(min_value, max_value)  # Set slider range
        slider.setValue(value)
        slider.setSingleStep(1) # Set step size
        slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        # slider.setTickInterval(tick_interval) # Set tick interval (used when showing ticks)
           
        # callback function
        slider.valueChanged.connect(lambda value: self._update_joint_value(title, joint_number, value))

        # value label
        value_label = self.create_label(str(value), size=10, alignment=QtCore.Qt.AlignCenter, color=QColor('black'), bold=False)

        slider.valueChanged.connect(lambda value: value_label.setText(str(value)))

        # Store the slider reference in the sliders dictionary (for later access)
        self.sliders[f'{title}_{joint_number}'] = slider
             # Initialize the joint value to 0
        self.joint_values[f'{title}_{joint_number}'] = value

        # create layout
        slider_layout.addWidget(min_label)
        slider_layout.addWidget(slider)
        slider_layout.addWidget(max_label)

        # add slider layout to the main layout
        layout.addWidget(value_label)
        layout.addLayout(slider_layout)

        # # Create a QWidget to hold the layout
        # widget = QtWidgets.QWidget()
        # widget.setLayout(layout)

        # # Wrap the QWidget in a QGraphicsProxyWidget
        # proxy_widget = QtWidgets.QGraphicsProxyWidget()
        # proxy_widget.setWidget(widget)

        # # Add the proxy widget to the layout at the appropriate row and column
        # self.win.addItem(proxy_widget, row, col)  # Correct method signature

        return layout
    
    def _update_joint_value(self, finger_name, joint_number, value):
        """
        Update the joint value in the dictionary.
        """
        self.joint_values[f"{finger_name}_{joint_number}"] = value
        print("Joint values: ", self.joint_values)

    def get_joint_values(self):
        """
        Return the current values of all sliders.
        """
        return self.joint_values

   

    def _create_sliders(self):
        """
        Create sliders dynamically for each row and column and add them to the layout
        within the GraphicsLayoutWidget (self.win).
        """
        for i in range(self.rows):
            for j in range(self.cols):
                # Create a slider
                slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
                slider.setRange(1, 100)  # Set slider range
                slider.setValue(50)  # Initial slider value
                slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
                slider.setTickInterval(10)

                # Connect the slider to the update function (optional, we update the value directly)
                slider.valueChanged.connect(lambda value, i=i, j=j: self._update_slider_value(i, j, value))

                # Store the slider in the sliders dictionary
                self.sliders[f"{i}_{j}"] = slider

                # Create a QGraphicsWidget to hold the slider
                graphics_widget = pg.GraphicsWidget()

                # Create a layout for the slider and add it to the GraphicsWidget
                slider_layout = QtWidgets.QVBoxLayout()
                slider_layout.addWidget(slider)
                widget = QtWidgets.QWidget()
                widget.setLayout(slider_layout)

                # Wrap the QWidget in a QGraphicsProxyWidget
                proxy_widget = QtWidgets.QGraphicsProxyWidget()
                proxy_widget.setWidget(widget)

                # Add the proxy widget to the layout at the appropriate row and column
                self.win.addItem(proxy_widget, i, j)  # Correct method signature

    def _update_slider_value(self, row, col, value):
        """
        Update the slider value in the dictionary.
        """
        self.slider_values[f"{row}_{col}"] = value
        print(f"Slider value at row {row}, col {col} is {value}")

    def get_slider_values(self):
        """
        Return the current values of all sliders.
        """
        return self.slider_values

    def run(self):
        """
        Start the application loop to show the window and handle events.
        """
        self.app.exec_()


def main():
    # Example usage of the SliderControl class
    slider_control = SliderControl(rows=4, cols=5, win=None)
    slider_control.run()
    # print(slider_control.get_slider_values())


if __name__ == '__main__':
    main()
