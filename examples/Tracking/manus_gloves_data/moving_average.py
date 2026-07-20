"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Simple fixed-size rolling-window moving average smoothing filters."""

class MovingAverage:
    """A fixed-size rolling window average over a single stream of values."""

    def __init__(self, window_size=10):
        """Initializes an empty rolling window.

        Args:
            window_size: Maximum number of most recent values to average
                over.
        """
        self.window_size = window_size
        self.window = []
        self.sum = 0

    def add(self, value):
        """Adds a new sample to the window, evicting the oldest if full.

        Args:
            value: The new sample to add.
        """
        self.window.append(value)
        self.sum += value
        if len(self.window) > self.window_size:
            self.sum -= self.window.pop(0)
        #print("Sum: ",self.sum)

    def get_average(self):
        """Returns the current average of the values in the window.

        Returns:
            The mean of the values currently in the window, or 0 if the
            window is empty.
        """
        if len(self.window) == 0:
            return 0
        return self.sum / len(self.window)


class MultiMovingAverage:
    """Manages a parallel set of independent MovingAverage windows.

    Useful for smoothing several related value streams (e.g. one per joint)
    together, where add_values() and get_averages() operate on all windows
    at once, aligned by position.
    """

    def __init__(self, window_size=10, num_windows=3):
        """Initializes num_windows independent MovingAverage instances.

        Args:
            window_size: Maximum number of most recent values each window
                averages over.
            num_windows: Number of independent moving-average windows to
                maintain.
        """
        self.window_size = window_size
        self.num_windows = num_windows
        self.windows = [MovingAverage(window_size) for _ in range(num_windows)]
        self.current_window = 0

    def add_values(self, values):
        """Adds one new sample to each window, in positional order.

        Args:
            values: Sequence of new samples, one per window, matched to
                self.windows by position via zip (extra values beyond
                num_windows are ignored).
        """
        for value, window in zip(values, self.windows):
            window.add(value)
        self.current_window = (self.current_window + 1) % self.num_windows

    def get_averages(self):
        """Returns the current average of each window.

        Returns:
            A list of the current moving average for each window, in the
            same order as self.windows.
        """
        return [window.get_average() for window in self.windows]


def test_multi_moving_average():
    """Manually exercises MultiMovingAverage by printing running averages of a linear ramp."""
    multi_moving_average = MultiMovingAverage(window_size=10, num_windows=5)
    for i in range(100):
        multi_moving_average.add_values([i, 2*i, 3*i, 4*i, 5*i])
        print(multi_moving_average.get_averages())


if __name__ == '__main__':
    test_multi_moving_average()