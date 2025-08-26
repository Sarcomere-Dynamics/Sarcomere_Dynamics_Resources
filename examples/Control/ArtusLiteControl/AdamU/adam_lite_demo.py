import socket
import logging
import time
import threading
import os
import sys
import json
import queue
from datetime import datetime
from typing import Dict, Any, Optional


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
sys.path.append(PROJECT_ROOT)

from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True  # Ensure logs propagate to parent loggers

# Constants for Setting Up
COM_METHOD='UDP'
COM_CHANNEL_LEFT='secret-ssid'
COM_CHANNEL_RIGHT='secret-ssid'

STREAM_FREQ = 10
START = True
CALIBRATE = False
STREAM = True

class HumanoidLite:
    def __init__(self, communication_method=COM_METHOD,
                 communication_channel_left=COM_CHANNEL_LEFT,
                 communication_channel_right=COM_CHANNEL_RIGHT,
                  communication_frequency=STREAM_FREQ,
                 calibration_flag=CALIBRATE,
                 stream_flag=STREAM):
        # expectation here is that two hands should be connected, a right and a left
        self.artus_left = ArtusAPI(communication_method=communication_method, 
                                   communication_channel_identifier=communication_channel_left,
                                   robot_type='artus_lite', hand_type='left',
                                   communication_frequency=communication_frequency,
                                   stream=STREAM, logger=logger)
        self.artus_right = ArtusAPI(communication_method=communication_method, 
                                    communication_channel_identifier=communication_channel_right,
                                    robot_type='artus_lite', hand_type='right',
                                    communication_frequency=communication_frequency, 
                                    stream=STREAM, logger=logger)

        self.hands = [self.artus_left, self.artus_right]
        self.require_calibration = calibration_flag
        self.stream_flag = stream_flag
        
        # Thread-safe queues for data sharing between threads
        self.hand_data_queue = queue.Queue()  # Hand data to send to socket
        self.socket_command_queue = queue.Queue()  # Commands from socket to hands
        
        # Thread control
        self.running = threading.Event()
        self.running.set()
        
        # Socket connection attributes
        self.server = None
        self.conn = None
        self.addr = None
        self._receive_buffer = ""  # Buffer for incoming messages

    def create_socket_server(self):
        """Create and configure the socket server"""
        # listen on all interfaces
        self.host = "0.0.0.0"
        self.port = 7364  # sd in ascii to hex (should be integer)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse
        self.server.bind((self.host, self.port))
        self.server.listen(1)  # Accept 1 connection

        logger.info(f"Socket Created and Listening on {self.host}:{self.port}")

    def accept_socket_connection(self):
        """Accept incoming socket connection (blocking call)"""
        self.conn, self.addr = self.server.accept()
        self._receive_buffer = ""  # Reset buffer for new connection
        logger.info(f"Connected by {self.addr}")
        return True

    def start_hands(self):
        """Initialize and start communication with both hands"""
        for hand in self.hands:
            hand.connect()
            time.sleep(0.1)

            if self.require_calibration:
                hand.calibrate()
                time.sleep(0.5)

    def hand_communication_thread(self):
        """Thread function for continuous hand data communication"""
        logger.info("Starting hand communication thread")
        
        while self.running.is_set():
            try:
                # Check for commands from socket to send to hands
                try:
                    command = self.socket_command_queue.get_nowait()
                    self.process_hand_command(command)
                except queue.Empty:
                    pass
                
                # Get hand data and put it in queue for socket transmission
                hand_data = self.get_hand_data()
                if hand_data:
                    try:
                        self.hand_data_queue.put_nowait(hand_data)
                    except queue.Full:
                        # If queue is full, remove oldest and add new
                        try:
                            self.hand_data_queue.get_nowait()
                            self.hand_data_queue.put_nowait(hand_data)
                        except queue.Empty:
                            pass
                
                time.sleep(1.0 / STREAM_FREQ)  # Control loop frequency
                
            except Exception as e:
                logger.error(f"Error in hand communication thread: {e}")
                time.sleep(0.1)
        
        logger.info("Hand communication thread stopped")

    def socket_receive_thread(self):
        """Thread function for receiving data from socket"""
        logger.info("Starting socket receive thread")
        
        while self.running.is_set():
            try:
                if self.conn:
                    # Set socket timeout to avoid blocking indefinitely
                    self.conn.settimeout(1.0)
                    try:
                        # Receive data with a reasonable buffer size
                        data = self.conn.recv(4096)
                        if data:
                            try:
                                # Add received data to buffer
                                self._receive_buffer += data.decode('utf-8')
                                
                                # Process complete messages (delimited by newlines)
                                while '\n' in self._receive_buffer:
                                    line, self._receive_buffer = self._receive_buffer.split('\n', 1)
                                    if line.strip():  # Skip empty lines
                                        try:
                                            # Parse JSON command
                                            command = json.loads(line.strip())
                                            logger.info(f"Received JSON command from socket: {command}")
                                            self.socket_command_queue.put(command)
                                        except json.JSONDecodeError as e:
                                            logger.error(f"Invalid JSON received: {e} - Line: {line}")
                                        
                            except Exception as e:
                                logger.error(f"Error processing received data: {e}")
                        else:
                            # Connection closed by client
                            logger.info("Socket connection closed by client")
                            self.conn = None
                            self._receive_buffer = ""  # Clear buffer on disconnect
                            time.sleep(1.0)
                    except socket.timeout:
                        # Normal timeout, continue loop
                        pass
                    except ConnectionResetError:
                        logger.warning("Socket connection reset")
                        self.conn = None
                        self._receive_buffer = ""  # Clear buffer on connection reset
                        time.sleep(1.0)
                else:
                    time.sleep(1.0)  # Wait for connection
                    
            except Exception as e:
                logger.error(f"Error in socket receive thread: {e}")
                time.sleep(1.0)
        
        logger.info("Socket receive thread stopped")

    def socket_send_thread(self):
        """Thread function for sending data to socket"""
        logger.info("Starting socket send thread")
        
        while self.running.is_set():
            try:
                if self.conn:
                    try:
                        # Get hand data from queue
                        hand_data = self.hand_data_queue.get(timeout=1.0)
                        
                        # Send data as JSON with datetime support
                        json_data = json.dumps(hand_data, cls=DateTimeEncoder)
                        self.conn.sendall(json_data.encode('utf-8') + b'\n')
                        
                    except queue.Empty:
                        # No data to send, continue
                        pass
                    except (ConnectionResetError, BrokenPipeError):
                        logger.warning("Socket connection lost during send")
                        self.conn = None
                else:
                    time.sleep(1.0)  # Wait for connection
                    
            except Exception as e:
                logger.error(f"Error in socket send thread: {e}")
                time.sleep(1.0)
        
        logger.info("Socket send thread stopped")

    def get_hand_data(self) -> Optional[Dict[str, Any]]:
        """Get current data from both hands"""
        try:
            if not self.stream_flag:
                return None

            data = {
                'timestamp': datetime.now(),
                'left_hand': None,
                'right_hand': None
            }
            
            # Get data from left hand
            try:
                left_result = self.artus_left.get_streamed_joint_angles()
                if left_result:
                    ack, vals = left_result
                    angles = vals[:16]
                    velocities = vals[16:32]
                    data['left_hand'] = {
                        'angles': angles,
                        'velocities': velocities
                    }
            except Exception as e:
                logger.warning(f"Failed to get left hand data: {e}")
            
            # Get data from right hand
            try:
                right_result = self.artus_right.get_streamed_joint_angles()
                if right_result:
                    ack, vals = right_result
                    angles = vals[:16]
                    velocities = vals[16:32]
                    data['right_hand'] = {
                        'angles': angles,
                        'velocities': velocities
                    }
            except Exception as e:
                logger.warning(f"Failed to get right hand data: {e}")

            # Log the collected data
            logger.debug(f"Hand data at {data['timestamp']}: {data}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting hand data: {e}")
            return None

    def create_empty_joint_dict(self):
        """Create an empty joint dictionary for a hand"""
        joint_dict = {
            'index': 0,
            'target_angle': 0,
            'velocity': 60
        }
        return joint_dict

    def create_empty_joint_dict_list(self):
        """Create a list of empty joint dictionaries for a hand"""
        joint_dict_list = {}
        for i in range(16):
            joint_dict_list[f'{i}'] = self.create_empty_joint_dict()
        return joint_dict_list

    def process_hand_command(self, command: Dict[str, Any]):
        """Process commands received from socket and send to appropriate hand
        
        Expected JSON command format:
        {
            'time': datetime string (ISO format) or timestamp,
            'left': [16 joint angles for left hand],
            'right': [16 joint angles for right hand]
        }
        """
        try:
            # Validate command format
            if not isinstance(command, dict):
                logger.error("Command must be a dictionary/JSON object")
                return
            
            # Check for required fields
            if 'time' not in command:
                logger.error("Command missing 'time' field")
                return
            
            # Parse the time field - could be datetime string, timestamp, or datetime object
            command_time_raw = command['time']
            if isinstance(command_time_raw, str):
                try:
                    # Try to parse as ISO format datetime string
                    command_time = datetime.fromisoformat(command_time_raw.replace('Z', '+00:00'))
                except ValueError:
                    logger.error(f"Invalid datetime format: {command_time_raw}")
                    return
            elif isinstance(command_time_raw, (int, float)):
                # Convert timestamp to datetime
                command_time = datetime.fromtimestamp(command_time_raw)
            elif isinstance(command_time_raw, datetime):
                # Already a datetime object
                command_time = command_time_raw
            else:
                logger.error(f"Invalid time format: {type(command_time_raw)}")
                return
                
            logger.info(f"Processing command with datetime: {command_time}")
            
            # Process left hand command if present
            if 'left' in command:
                left_angles = command['left']
                if isinstance(left_angles, list) and len(left_angles) == 16:
                    # Create joint angles dictionary for left hand
                    left_joint_dict = self.create_empty_joint_dict_list()
                    for i, angle in enumerate(left_angles):
                        left_joint_dict[f'{i}']['target_angle'] = int(angle)
                        left_joint_dict[f'{i}']['index'] = i
                    
                    # Send to left hand
                    self.artus_left.set_joint_angles(left_joint_dict)
                    logger.info(f"Sent left hand command with {len(left_angles)} angles")
                else:
                    logger.error(f"Left hand angles must be a list of 16 values, got: {type(left_angles)} with length {len(left_angles) if isinstance(left_angles, list) else 'N/A'}")
            
            # Process right hand command if present
            if 'right' in command:
                right_angles = command['right']
                if isinstance(right_angles, list) and len(right_angles) == 16:
                    # Create joint angles dictionary for right hand
                    right_joint_dict = self.create_empty_joint_dict_list()
                    for i, angle in enumerate(right_angles):
                        right_joint_dict[f'{i}']['target_angle'] = int(angle)
                        right_joint_dict[f'{i}']['index'] = i
                    
                    # Send to right hand
                    self.artus_right.set_joint_angles(right_joint_dict)
                    logger.info(f"Sent right hand command with {len(right_angles)} angles")
                else:
                    logger.error(f"Right hand angles must be a list of 16 values, got: {type(right_angles)} with length {len(right_angles) if isinstance(right_angles, list) else 'N/A'}")
                     
        except Exception as e:
            logger.error(f"Error processing hand command: {e}")

    def start_threads(self):
        """Start all communication threads"""
        logger.info("Starting all threads...")
        
        # Create threads
        self.hand_thread = threading.Thread(target=self.hand_communication_thread, daemon=True)
        self.socket_recv_thread = threading.Thread(target=self.socket_receive_thread, daemon=True)
        self.socket_send_thread = threading.Thread(target=self.socket_send_thread, daemon=True)
        
        # Start threads
        self.hand_thread.start()
        self.socket_recv_thread.start()
        self.socket_send_thread.start()
        
        logger.info("All threads started successfully")

    def send_hands_to_home(self):
        """Send both hands to home position (0 degrees) for safety"""
        try:
            logger.info("Sending hands to home position...")
            
            for hand in self.hands:
                try:
                    hand.set_home_position()
                    logger.info(f"Sent {hand.robot_handler.hand_type} hand to home position")
                except Exception as e:
                    logger.error(f"Failed to send {hand.robot_handler.hand_type} hand to home: {e}")
            
            # Give hands time to move to home position
            time.sleep(2.0)
            logger.info("Hands moved to home position")
            
        except Exception as e:
            logger.error(f"Error sending hands to home position: {e}")

    def sleep_hands(self):
        """Put both hands to sleep for safe shutdown"""
        try:
            logger.info("Putting hands to sleep...")
            
            for i,hand in enumerate(self.hands):
                try:
                    result = hand.sleep()
                    logger.info(f"Sent sleep command to hand {i}")
                except Exception as e:
                    logger.error(f"Failed to sleep hand {i}: {e}")
            
            # Give hands time to complete sleep sequence
            time.sleep(1.0)
            logger.info("Hands are now sleeping")
            
        except Exception as e:
            logger.error(f"Error putting hands to sleep: {e}")

    def stop_threads(self):
        """Stop all threads gracefully"""
        logger.info("Stopping threads...")
        self.running.clear()
        
        # Close socket connections
        if self.conn:
            self.conn.close()
        if self.server:
            self.server.close()
        
        logger.info("Threads stopped")

    def run(self):
        """Main execution function"""
        try:
            # Setup logging
            logging.basicConfig(level=logging.INFO, 
                              format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            logger.info("Initializing HumanoidLite for Raspberry Pi 5...")
            
            # Start hands
            logger.info("Connecting to hands...")
            self.start_hands()
            
            # Create socket server
            logger.info("Creating socket server...")
            self.create_socket_server()
            
            # Start communication threads
            self.start_threads()
            
            # Wait for socket connection and handle it
            logger.info("Waiting for socket connection...")
            while self.running.is_set():
                try:
                    if not self.conn:
                        self.accept_socket_connection()
                    time.sleep(1.0)
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Error in main execution: {e}")
        finally:
            # Safe shutdown sequence: Home -> Sleep -> Stop
            self.send_hands_to_home()
            self.sleep_hands()
            self.stop_threads()


def main():
    """Entry point for the application"""
    humanoid = HumanoidLite()
    try:
        humanoid.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        # Safe shutdown sequence: Home -> Sleep -> Stop
        humanoid.send_hands_to_home()
        humanoid.sleep_hands()
        humanoid.stop_threads()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Safe shutdown sequence: Home -> Sleep -> Stop
        humanoid.send_hands_to_home()
        humanoid.sleep_hands()
        humanoid.stop_threads()
    finally:
        logger.info("Application shutting down")


if __name__ == "__main__":
    main()
