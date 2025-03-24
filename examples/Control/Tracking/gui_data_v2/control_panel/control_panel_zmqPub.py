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



import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data_v2.control_panel.control_panel import ControlPanelWidget


class ControlPanelWidgetZQM(ControlPanelWidget):
    """
    Same as ControlPanelWidget but with ZeroMQ publisher for sending slider commands to the robot
    """
    def __init__(self, slider_control=None, win=None, zmq_sliderCommands_pubPort = 5556, hand_poses_directory="//"):

        super().__init__(slider_control=slider_control, win=win, hand_poses_directory=hand_poses_directory)
        
        self.zmq_sliderCommands_pubPort = zmq_sliderCommands_pubPort
        self._setup_zmq_publisher(address="tcp://127.0.0.1:" + str(self.zmq_sliderCommands_pubPort))

    def _setup_zmq_publisher(self, address):
        """
        Setup the ZeroMQ publisher for sending slider commands to the robot
        """
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQPublisher
        self.zmq_publisher = ZMQPublisher(address=address)

    def send_data(self):
        """
        Send data to the ZeroMQ publisher
        example: {"Thumb_1": 0.0, "Thumb_2": 0.0, "Thumb_3": 0.0, "Thumb_4": 0.0,
                "Index_1": 0.0, "Index_2": 0.0, "Index_3": 0.0,
                "Middle_1": 0.0, "Middle_2": 0.0, "Middle_3": 0.0,
                "Ring_1": 0.0, "Ring_2": 0.0, "Ring_3": 0.0}
        """
        data = self.slider_control.get_joint_values()
        self.zmq_publisher.send(topic="GUI",
                                message=json.dumps(data))
        
        # print("Data Sent: ", json.dumps(data))




def main():
    app = QtWidgets.QApplication([])

    main_window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    # Create a GraphicsLayoutWidget for the control window
    # win = pg.GraphicsLayoutWidget(show=True)

    controlPanel_and_sliders_layout = QtWidgets.QHBoxLayout()

    # Create a SliderControl instance
    import os
    import sys
    sys.path.append(PROJECT_ROOT)
    from gui.sliders_commands.slider_class import SliderControl
    # Create a SliderControl instance
    slider_control = SliderControl(rows=5, cols=4)

    # Create a ControlPanelWidget instance
    control_panel = ControlPanelWidgetZQM(slider_control)

    layout.addWidget(control_panel, 0, QtCore.Qt.AlignTop)
    controlPanel_and_sliders_layout.addWidget(slider_control.win)

    layout.addLayout(controlPanel_and_sliders_layout)


    main_window.setLayout(layout)
    main_window.setWindowTitle("Control Panel")
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()
    app.exec_()



if __name__ == '__main__':
    main()
