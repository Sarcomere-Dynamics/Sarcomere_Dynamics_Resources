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


import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
# from gui.feedback_visualization.display_class import RealTimePlots
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data_v2.feedback_visualization.display_class_zmqSub import RealTimePlotsZMQ as RealTimePlots
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data_v2.slider_commands.slider_class import SliderControl
sys.path.append(PROJECT_ROOT)
# from gui.control_panel.control_panel import 
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data_v2.control_panel.control_panel_zmqPub import ControlPanelWidgetZQM as ControlPanelWidget


# Main GUI Class
class ArtusLiteGUI:
    """
    Creates the main GUI for interacting with the Artus Lite robot
    Publishes data from the GUI to the ZMQ server
    Subscribes to feedback data from the ZMQ server to display in the GUI
    """
    def __init__(self, rows=5, cols=4,
                 control_hand=True,
                 show_feedback=True,
                 zmq_sliderCommands_pubPort = 5556,
                 zmq_feedback_subPort = 5555):
        
         # directory path to save the joint positions
        self.directory = str(PROJECT_ROOT) + "//Sarcomere_Dynamics_Resources//examples//Control//ArtusLiteControl//GUIControlV2//hand_pose_data//"
        
        self.app = QtWidgets.QApplication([])
        # Set up the main window layout
        self.main_window = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()

        # Another layout for the sliders and plots
        slider_and_plot_layout = QtWidgets.QHBoxLayout()
        if control_hand:
            # Create the SliderControl
            self.slider_control = SliderControl(rows=rows, cols=cols)
            # Create control panel and add it to the layout (below the sliders/plots)
            self.control_panel = ControlPanelWidget(slider_control=self.slider_control,
                                                    zmq_sliderCommands_pubPort = zmq_sliderCommands_pubPort,
                                                    win=self.slider_control.win,
                                                    hand_poses_directory = self.directory)
            # add panel horizontally at the top
            self.layout.addWidget(self.control_panel, 0, QtCore.Qt.AlignTop)
            
            slider_and_plot_layout.addWidget(self.slider_control.win)

            self.zmq_sliderCommands_pubPort = zmq_sliderCommands_pubPort
            # self._setup_zmq_publisher(address="tcp://127.0.0.1:" + str(self.zmq_sliderCommands_pubPort))

        if show_feedback:
            # Create the RealTimePlots object
            self.plot_control = RealTimePlots(rows=rows, cols=cols,
                                              zmq_feedback_subPort = zmq_feedback_subPort)
            slider_and_plot_layout.addWidget(self.plot_control.win)
            self.zmq_feedback_subPort = zmq_feedback_subPort
            # self._setup_zmq_subscriber(address = "tcp://127.0.0.1:" + str(self.zmq_feedback_subPort))
            
        # Add the slider and plot layout to the main layout
        self.layout.addLayout(slider_and_plot_layout)
            
  
    
        # Set the main window layout
        self.main_window.setLayout(self.layout)
        self.main_window.setWindowTitle('ArtusLite Control GUI')
        self.main_window.setGeometry(100, 100, 800, 600)  # Set window size
        self.main_window.show()

    def run(self):
        """
        Start the application loop.
        """
        self.app.exec_()


def main():
    gui = ArtusLiteGUI(rows=4, cols=5,
                        control_hand=True, 
                        show_feedback=True)


    # gui = ArtusLiteGUI(rows=4, cols=5,
    #                     control_hand=True,
    #                     show_feedback=False)
    gui.run()


if __name__ == '__main__':
    main()