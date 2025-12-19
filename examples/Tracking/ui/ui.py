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
import sys
from PySide6 import QtWidgets

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

from examples.Tracking.ui.ui_control import UIControl
from examples.Tracking.ui.ui_feedback import UIFeedback

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
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
        self.control_panel.send_data()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
