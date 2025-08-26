#!/usr/bin/env python3
"""
Socket Client for HumanoidLite Communication

This client interfaces with the HumanoidLite socket server to send commands
and receive hand data. Simple, non-threaded design for easy integration.

Author: AI Assistant
Date: 2024
"""

import socket
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class HumanoidLiteClient:
    """Simple client for communicating with HumanoidLite socket server"""
    
    def __init__(self, host: str = "localhost", port: int = 7364, timeout: float = 5.0):
        """
        Initialize the client
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            timeout: Socket timeout for operations in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        
        # Socket and connection state
        self.socket = None
        self.connected = False
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Data buffer for partial messages
        self._buffer = ""
        
    def connect(self) -> bool:
        """
        Connect to the HumanoidLite server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.connected and self.socket:
                return True
                
            # Clean up any existing socket
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
                
            self.logger.info(f"Attempting to connect to {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self._buffer = ""  # Reset buffer on new connection
            self.logger.info(f"Successfully connected to HumanoidLite server at {self.host}:{self.port}")
            return True
        except socket.timeout:
            self.logger.error(f"Connection timeout to {self.host}:{self.port}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
        except ConnectionRefusedError:
            self.logger.error(f"Connection refused by {self.host}:{self.port} - is the server running?")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to server {self.host}:{self.port}: {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
        self._buffer = ""
        self.logger.info("Disconnected from server")
    
    def send_command(self, left_angles: Optional[List[int]] = None, 
                    right_angles: Optional[List[int]] = None,
                    timestamp: Optional[datetime] = None) -> bool:
        """
        Send joint angle commands to the hands
        
        Args:
            left_angles: List of 16 joint angles for left hand (optional)
            right_angles: List of 16 joint angles for right hand (optional)
            timestamp: Command timestamp (uses current time if None)
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.connected or not self.socket:
            if not self.connect():
                return False
        
        # Validate angle arrays
        if left_angles and len(left_angles) != 16:
            self.logger.error(f"Left hand angles must be exactly 16 values, got {len(left_angles)}")
            return False
        
        if right_angles and len(right_angles) != 16:
            self.logger.error(f"Right hand angles must be exactly 16 values, got {len(right_angles)}")
            return False
        
        # Create command dictionary
        command = {
            "time": timestamp or datetime.now()
        }
        
        if left_angles:
            command["left"] = left_angles
        
        if right_angles:
            command["right"] = right_angles
        
        try:
            # Send JSON command with newline terminator
            json_data = json.dumps(command, cls=DateTimeEncoder)
            message = json_data + '\n'
            self.socket.sendall(message.encode('utf-8'))
            self.logger.info(f"Sent command: {json_data}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            self.connected = False
            return False
    
    def send_raw_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a raw command dictionary to the server
        
        Args:
            command: Command dictionary to send
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.connected or not self.socket:
            if not self.connect():
                return False
        
        try:
            json_data = json.dumps(command, cls=DateTimeEncoder)
            message = json_data + '\n'
            self.socket.sendall(message.encode('utf-8'))
            self.logger.info(f"Sent raw command: {json_data}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send raw command: {e}")
            self.connected = False
            return False
    
    def receive_data(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive and parse data from the server (non-blocking if timeout=0)
        
        Args:
            timeout: Socket timeout in seconds. None uses default, 0 for non-blocking
            
        Returns:
            Dict containing hand data or None if no data available
        """
        if not self.connected or not self.socket:
            return None
        
        try:
            # Set socket timeout
            original_timeout = self.socket.gettimeout()
            if timeout is not None:
                self.socket.settimeout(timeout)
            
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.logger.warning("Server closed connection")
                    self.connected = False
                    return None
                
                # Decode and buffer the data
                self._buffer += data.decode('utf-8')
                
                # Process complete JSON messages (separated by newlines)
                while '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    if line.strip():
                        try:
                            # Parse JSON data
                            hand_data = json.loads(line.strip())
                            
                            # Parse timestamp if it's a string
                            if 'timestamp' in hand_data and isinstance(hand_data['timestamp'], str):
                                try:
                                    hand_data['timestamp'] = datetime.fromisoformat(
                                        hand_data['timestamp'].replace('Z', '+00:00')
                                    )
                                except ValueError:
                                    pass  # Keep as string if parsing fails
                            
                            return hand_data
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON received: {e}")
                            continue
                
                return None  # No complete message yet
                
            finally:
                # Restore original timeout
                if timeout is not None:
                    self.socket.settimeout(original_timeout)
                
        except socket.timeout:
            # Normal timeout, no data available
            return None
        except ConnectionResetError:
            self.logger.warning("Connection reset by server")
            self.connected = False
            return None
        except Exception as e:
            self.logger.error(f"Error receiving data: {e}")
            self.connected = False
            return None
    
    def is_connected(self) -> bool:
        """Check if client is connected to server"""
        return self.connected
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def simple_example():
    """Simple usage example for integration into other scripts"""
    # Setup logging (optional)
    # logging.basicConfig(level=logging.INFO)
    
    # Create and connect client
    client = HumanoidLiteClient(host="localhost", port=7364)
    
    if not client.connect():
        print("Failed to connect to server")
        return
    
    print("Connected to server!")
    
    try:
        # Send command to both hands
        left_angles = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        right_angles = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        
        success = client.send_command(left_angles=left_angles, right_angles=right_angles)
        print(f"Command sent: {success}")
        
        # Receive some data
        for i in range(5):
            data = client.receive_data(timeout=1.0)
            if data:
                timestamp = data.get('timestamp', 'N/A')
                print(f"Received data at {timestamp}")
                
                if data.get('left_hand'):
                    left_angles = data['left_hand'].get('angles', [])
                    print(f"  Left hand angles: {left_angles[:5]}...")
                
                if data.get('right_hand'):
                    right_angles = data['right_hand'].get('angles', [])
                    print(f"  Right hand angles: {right_angles[:5]}...")
            else:
                print("No data received")
            
            time.sleep(0.5)
    
    finally:
        client.disconnect()
        print("Disconnected")


def context_manager_example():
    """Example using context manager for automatic cleanup"""
    with HumanoidLiteClient(host="localhost", port=7364) as client:
        if client.is_connected():
            print("Connected successfully!")
            
            # Send a simple command first
            left_angles = [0] * 16
            right_angles = [0] * 16
            
            success = client.send_command(left_angles=left_angles, right_angles=right_angles)
            print(f"Command sent successfully: {success}")
            
            if success:
                # Get response
                data = client.receive_data(timeout=2.0)
                if data:
                    print(f"Received data: {data}")
                else:
                    print("No response received")
            else:
                print("Failed to send command")
        else:
            print("Failed to connect")


def continuous_example():
    """Example with continuous loop for testing"""
    print("Starting continuous example...")
    
    client = HumanoidLiteClient(host="localhost", port=7364)
    
    if not client.connect():
        print("Failed to connect to server")
        return
    
    print("Connected! Starting continuous loop...")
    
    try:
        i = 0
        increment = True
        
        for iteration in range(100):  # Run for 20 iterations
            print(f"\n--- Iteration {iteration + 1} ---")
            
            # Create angle pattern
            # left_angles = [i if j % 3 == 0 else 0 for j in range(16)]
            # right_angles = [i if j % 3 == 0 else 0 for j in range(16)]
            ix = i*3
            left_angles =   [0,ix,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix]
            right_angles =  [0,ix,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix]
            
            # Send command
            success = client.send_command(left_angles=left_angles, right_angles=right_angles)
            print(f"Sent command (i={i}): {success}")
            
            if not success:
                print("Failed to send command, attempting to reconnect...")
                if not client.connect():
                    print("Reconnection failed, exiting")
                    break
                continue
            
            # Update counter
            if increment:
                i += 1
                if i >= 25:
                    increment = False
            else:
                i -= 1
                if i <= 0:
                    increment = True
            
            # Try to receive data
            data = client.receive_data(timeout=0.5)
            if data:
                timestamp = data.get('timestamp', 'N/A')
                print(f"Received data at {timestamp}")
                
                if data.get('left_hand'):
                    left_received = data['left_hand'].get('angles', [])
                    print(f"  Left hand angles: {left_received[:3]}...")
            else:
                print("No data received this iteration")
            
            time.sleep(0.1)  # Small delay between iterations

        ix = 0
        left_angles =   [0,ix,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix]
        right_angles =  [0,ix,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix,0,ix,ix]
        
        # Send command
        success = client.send_command(left_angles=left_angles, right_angles=right_angles)

    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Choose an example to run:")
    print("1. Simple example")
    print("2. Context manager example") 
    print("3. Continuous example")
    
    choice = input("Enter choice (1-3) or press Enter for continuous: ").strip()
    
    if choice == "1":
        print("Running simple example...")
        simple_example()
    elif choice == "2":
        print("Running context manager example...")
        context_manager_example()
    else:
        print("Running continuous example...")
        continuous_example()
