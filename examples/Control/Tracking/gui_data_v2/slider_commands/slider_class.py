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


class EditableValueLabel(QtWidgets.QLabel):
    """
    A custom QLabel that supports double-click editing for joint values.
    """
    def __init__(self, text, title, joint_number, slider, min_value, max_value, parent=None):
        super().__init__(text, parent)
        self.title = title
        self.joint_number = joint_number
        self.slider = slider
        self.min_value = min_value
        self.max_value = max_value
        self.is_editing = False
        self.parent_controller = None
        
        # EditableValueLabel created
        
        # Set up the label appearance
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        self.setFont(font)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: black; 
                border: 1px solid transparent; 
                padding: 2px;
                background-color: transparent;
            }
            QLabel:hover {
                border: 1px solid gray; 
                background-color: #f0f0f0;
                cursor: pointer;
            }
        """)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Install event filter for more reliable event handling
        self.installEventFilter(self)
    
    def set_parent_controller(self, controller):
        """Set the parent controller to handle edit operations."""
        self.parent_controller = controller
    
    def reset_editing_state(self):
        """Reset the editing state if it gets stuck."""
        self.is_editing = False
        self.setStyleSheet("""
            QLabel {
                color: black; 
                border: 1px solid transparent; 
                padding: 2px;
                background-color: transparent;
            }
            QLabel:hover {
                border: 1px solid gray; 
                background-color: #f0f0f0;
                cursor: pointer;
            }
        """)
    
    def eventFilter(self, obj, event):
        """Event filter for more reliable mouse event handling."""
        if obj == self:
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                # Reset editing state if it's stuck
                if self.is_editing:
                    self.reset_editing_state()
                
                if event.button() == QtCore.Qt.LeftButton and self.parent_controller and not self.is_editing:
                    self.parent_controller._start_edit_value(self)
                    return True
            elif event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    pass  # Single click detected
            elif event.type() == QtCore.QEvent.Enter:
                pass  # Mouse entered
            elif event.type() == QtCore.QEvent.Leave:
                pass  # Mouse left
        
        return super().eventFilter(obj, event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click events to start editing."""
        if event.button() == QtCore.Qt.LeftButton and self.parent_controller and not self.is_editing:
            self.parent_controller._start_edit_value(self)
        super().mouseDoubleClickEvent(event)
    
    def mousePressEvent(self, event):
        """Handle single click events."""
        if event.button() == QtCore.Qt.LeftButton:
            pass  # Single click detected
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter events for hover effects."""
        if not self.is_editing:
            self.setStyleSheet("""
                QLabel {
                    color: black; 
                    border: 1px solid gray; 
                    padding: 2px;
                    background-color: #f0f0f0;
                    cursor: pointer;
                }
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave events for hover effects."""
        if not self.is_editing:
            self.setStyleSheet("""
                QLabel {
                    color: black; 
                    border: 1px solid transparent; 
                    padding: 2px;
                    background-color: transparent;
                }
            """)
        super().leaveEvent(event)


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
    
    def create_editable_value_label(self, text, title, joint_number, slider, min_value, max_value):
        """
        Create an editable value label that allows double-click to edit the value.
        """
        label = EditableValueLabel(text, title, joint_number, slider, min_value, max_value)
        label.set_parent_controller(self)
        return label
    
    def _start_edit_value(self, label):
        """
        Start editing the value label by replacing it with a line edit.
        """
        # Reset editing state if it's stuck
        if label.is_editing:
            label.reset_editing_state()
            return
        
        # Double-check that we're not already editing
        if label.is_editing:
            return
            
        label.is_editing = True
        
        # Create a line edit widget
        line_edit = QtWidgets.QLineEdit()
        line_edit.setText(label.text())
        line_edit.setAlignment(QtCore.Qt.AlignCenter)
        line_edit.setFont(label.font())
        line_edit.setStyleSheet("border: 2px solid blue; padding: 2px; background-color: white;")
        
        # Ensure the line edit is properly focused and ready for editing
        line_edit.setFocus()
        line_edit.activateWindow()
        line_edit.raise_()
        line_edit.selectAll()
        
        # Force the line edit to be editable
        line_edit.setReadOnly(False)
        line_edit.setEnabled(True)
        
        # Position the line edit over the label
        parent_widget = label.parent()
        if parent_widget:
            # Get the label's geometry relative to its parent
            label_rect = label.geometry()
            line_edit.setGeometry(label_rect)
        else:
            return
        
        # Set the line edit as a child of the same parent as the label
        line_edit.setParent(parent_widget)
        
        # Make the label transparent but keep it in layout to maintain space
        label.setStyleSheet("color: transparent; border: 1px solid transparent; padding: 2px; background-color: transparent;")
        line_edit.show()
        line_edit.raise_()  # Bring to front
        
        # Ensure the line edit gets focus after being shown
        QtCore.QTimer.singleShot(10, lambda: line_edit.setFocus())
        
        # Store reference to the line edit
        label.line_edit = line_edit
        
        # Connect signals
        line_edit.returnPressed.connect(lambda: self._finish_edit_value(label))
        line_edit.editingFinished.connect(lambda: self._finish_edit_value(label))
        
        # Handle focus out event properly
        def focus_out_event(event):
            self._finish_edit_value(label)
            QtWidgets.QLineEdit.focusOutEvent(line_edit, event)
        
        line_edit.focusOutEvent = focus_out_event
        
        # Install event filter on parent widget to detect clicks outside
        if parent_widget:
            self.click_filter = self._create_click_outside_filter(line_edit, label)
            parent_widget.installEventFilter(self.click_filter)
        
        # Handle escape key to cancel editing
        def key_press_event(event):
            if event.key() == QtCore.Qt.Key_Escape:
                self._cancel_edit_value(label)
            else:
                QtWidgets.QLineEdit.keyPressEvent(line_edit, event)
        
        line_edit.keyPressEvent = key_press_event
    
    def _finish_edit_value(self, label):
        """
        Finish editing and update the slider value.
        """
        if not label.is_editing or not hasattr(label, 'line_edit'):
            return
            
        line_edit = label.line_edit
        try:
            # Get the new value and validate it
            new_value = int(line_edit.text())
            
            # Clamp the value to the valid range
            new_value = max(label.min_value, min(label.max_value, new_value))
            
            # Update the slider value
            label.slider.setValue(new_value)
            
            # Update the joint value (this will trigger the ZMQ publisher)
            self._update_joint_value(label.title, label.joint_number, new_value)
            
        except ValueError:
            # If the input is not a valid integer, revert to the original value
            new_value = label.slider.value()
        
        # Restore the label
        self._restore_label(label, str(new_value))
    
    def _cancel_edit_value(self, label):
        """
        Cancel editing and restore the original value.
        """
        if not label.is_editing or not hasattr(label, 'line_edit'):
            return
            
        # Restore the label with the current slider value
        original_value = label.slider.value()
        self._restore_label(label, str(original_value))
    
    def _restore_label(self, label, text):
        """
        Restore the label widget and remove the line edit.
        """
        if not label.is_editing or not hasattr(label, 'line_edit'):
            return
            
        line_edit = label.line_edit
        
        # Hide the line edit and show the label
        line_edit.hide()
        line_edit.setParent(None)  # Remove from parent
        
        # Remove the click outside filter
        if hasattr(self, 'click_filter'):
            parent_widget = label.parent()
            if parent_widget:
                parent_widget.removeEventFilter(self.click_filter)
            delattr(self, 'click_filter')
        
        # Update the label text
        label.setText(text)
        
        # Clean up
        line_edit.deleteLater()
        delattr(label, 'line_edit')
        label.is_editing = False
        
        # Reset the label style
        label.setStyleSheet("""
            QLabel {
                color: black; 
                border: 1px solid transparent; 
                padding: 2px;
                background-color: transparent;
            }
            QLabel:hover {
                border: 1px solid gray; 
                background-color: #f0f0f0;
                cursor: pointer;
            }
        """)
        # Label restored
    
    def _create_click_outside_filter(self, line_edit, label):
        """Create an event filter to detect clicks outside the line edit."""
        class ClickOutsideFilter(QtCore.QObject):
            def __init__(self, line_edit, label, parent_controller):
                super().__init__()
                self.line_edit = line_edit
                self.label = label
                self.parent_controller = parent_controller
            
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    # If click is outside the line edit, finish editing
                    if obj != self.line_edit and not self.line_edit.geometry().contains(event.pos()):
                        self.parent_controller._finish_edit_value(self.label)
                        return True
                return False
        
        return ClickOutsideFilter(line_edit, label, self)
    
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

        # value label - make it editable on double-click
        value_label = self.create_editable_value_label(str(value), title, joint_number, slider, min_value, max_value)

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
