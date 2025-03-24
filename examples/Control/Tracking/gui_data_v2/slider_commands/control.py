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
import numpy as np

# import os
# import sys
# current_directory = os.path.dirname(os.path.abspath(__file__))
# print(current_directory)
# from display_class import RealTimePlots


# Set up the Qt application
app = QtWidgets.QApplication([])

# Create a GraphicsLayoutWidget (plot window)
win = pg.GraphicsLayoutWidget()
win.show()

# Add a plot to the window
plot = win.addPlot(title="Interactive Plot with Slider")

# Data for the plot
x = np.linspace(0, 100, 100)
y = np.sin(x)
curve = plot.plot(x, y)

# Create a slider
slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
slider.setRange(1, 100)  # Range of the slider
slider.setValue(50)  # Initial slider value
slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
slider.setTickInterval(10)

# Function to update the plot based on slider value
def update_plot(value):
    y = np.sin(x + value / 10.0)  # Shift the sine wave based on slider value
    curve.setData(x, y)

# Connect the slider's value change to the update function
slider.valueChanged.connect(update_plot)

# Set up a layout for the slider and the plot
layout = QtWidgets.QVBoxLayout()
layout.addWidget(slider)
layout.addWidget(win)

# plots = RealTimePlots(rows=5, col=4, win=win)
# layout.addWidget(plots.win)

# Create a QWidget to hold the layout
main_widget = QtWidgets.QWidget()
main_widget.setLayout(layout)

# Show the window with the slider and plot
main_widget.show()

# Start the application event loop
app.exec_()
