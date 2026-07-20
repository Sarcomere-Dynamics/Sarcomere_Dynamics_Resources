"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Top-level Qt application window combining live hand control and feedback UI."""

import os
import sys
from PySide6 import QtWidgets

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

from examples.Tracking.ui.ui_control import UIControl
from examples.Tracking.ui.ui_feedback import UIFeedback

class MainWindow(QtWidgets.QMainWindow):
    """Main application window combining the control and feedback panels.

    Lays out a UIControl panel (joint/force/speed sliders and send/save
    controls) alongside a UIFeedback panel (live plots of hand feedback
    data) in a single horizontal window.
    """

    def __init__(self):
        """Builds the window and instantiates the control and feedback panels."""
        super().__init__()
        self.setWindowTitle("Artus GUI")

        self.control_panel = UIControl()
        self.feedback_panel = UIFeedback()

        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.feedback_panel)
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)
    
    def receive_joint_angles(self):
        """Triggers the control panel to publish its current joint values.

        Delegates to self.control_panel.send_data(), which sends the
        panel's current joint/force/speed values over ZMQ.
        """
        self.control_panel.send_data()

def main():
    """Creates the QApplication, shows the main window, and starts the event loop."""
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
