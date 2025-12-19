"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

class MovingAverage:
    def __init__(self, window_size=10):
        self.window_size = window_size
        self.window = []
        self.sum = 0

    def add(self, value):
        self.window.append(value)
        self.sum += value
        if len(self.window) > self.window_size:
            self.sum -= self.window.pop(0)
        #print("Sum: ",self.sum)

    def get_average(self):
        if len(self.window) == 0:
            return 0
        return self.sum / len(self.window)


class MultiMovingAverage:
    def __init__(self, window_size=10, num_windows=3):
        self.window_size = window_size
        self.num_windows = num_windows
        self.windows = [MovingAverage(window_size) for _ in range(num_windows)]
        self.current_window = 0

    def add_values(self, values):
        for value, window in zip(values, self.windows):
            window.add(value)
        self.current_window = (self.current_window + 1) % self.num_windows

    def get_averages(self):
        return [window.get_average() for window in self.windows]
        
    
def test_multi_moving_average():
    multi_moving_average = MultiMovingAverage(window_size=10, num_windows=5)
    for i in range(100):
        multi_moving_average.add_values([i, 2*i, 3*i, 4*i, 5*i])
        print(multi_moving_average.get_averages())


if __name__ == '__main__':
    test_multi_moving_average()