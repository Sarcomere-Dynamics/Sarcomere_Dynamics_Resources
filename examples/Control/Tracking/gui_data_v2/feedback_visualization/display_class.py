"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from time import perf_counter

import numpy as np

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor


class RealTimePlots:
    def __init__(self, rows = 4, cols = 5, win = None):
        if win is None:
            self.win = pg.GraphicsLayoutWidget(show=True)
        else:
            self.win = win
            # self.win.show()
            self.win.setWindowTitle('Artus Lite Control')


        
        self.joint_values = {} # feedback forces

        self.finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        # Define colors
        self.colors = {
            "Thumb": QColor('violet'),
            "Index": QColor('blue'),
            "Middle": QColor('green'),
            "Ring": QColor('red'),
            "Pinky": QColor('orange')
        }

        # self.min_max_values = {
        #     "Thumb": [(-25,25), (0, 90), (0, 90), (0, 90)],
        #     "Index": [(-15, 15), (0, 90), (0, 90)],
        #     "Middle": [(-15, 15), (0, 90), (0, 90)],
        #     "Ring": [(-15, 15), (0, 90), (0, 90)],
        #     "Pinky": [(-15, 15), (0, 90), (0, 90)]
        # }


        self.rows = rows
        self.cols = cols

        # Create the plots
        self.plots = []
        self.data = []
        self.curves = []
        self.ptr = []
        self.counter = 0
        self.create_joint_plots()



    def create_joint_plots(self):

        # Create plots for fingers (four joints thumb, three joints for other fingers)
        for i in range(4):
            for j in range(5):
                if j != 0 and i == 3:
                    break
                self.plots.append(self.win.addPlot())
                self.data.append(np.random.normal(size=500))
                self.curves.append(self.plots[self.counter].plot(self.data[self.counter]))
                # color for each finger
                self.curves[self.counter].setPen(self.colors[self.finger_names[j]])
                self.counter += 1
                self.ptr.append(0)
            self.win.nextRow()
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        print("****** Data *******", self.data)
        self.timer.start(50)

    # def get_data_for_plots(self):
    #     return self.data


    def update(self):
        """
        Update the plots with new data
        *get data from the zmq subscriber and update the plots
        """
        new_data = self._get_data()
        counter = 0
        for i in range(4):
            for j in range(5):
                if j != 0 and i == 3:
                    break
                self.data[i*self.cols + j][:-1] = self.data[i*self.cols + j][1:] # 
                # self.data[i*self.cols + j][-1] = np.random.normal()
                self.data[i*self.cols + j][-1] =  new_data[counter]
                counter += 1
                self.curves[i*self.cols + j].setData(self.data[i*self.cols + j])
                self.curves[i*self.cols + j].setPos(self.ptr[i*self.cols + j], 0)
                self.ptr[i*self.cols + j] += 1


    def _get_data(self):
        """
        Get data from the zmq subscriber
        """
        # test data with random values (16 values for 4 fingers)
        data = np.zeros(16)
        #for thumb show sine waves
        data[0] = np.sin(2 * np.pi * perf_counter() / 10)
        data[1] = np.sin(2 * np.pi * perf_counter() / 10)
        data[2] = np.sin(2 * np.pi * perf_counter() / 10)
        data[3] = np.sin(2 * np.pi * perf_counter() / 10)
        # for other fingers show random values
        for i in range(4, 16):
            data[i] = np.random.normal()
        return data



def main():
    # Set up the Qt application
    app = pg.mkQApp()
    real_time_plots = RealTimePlots(win=None)
    app.exec_()


if __name__ == '__main__':
    main()
