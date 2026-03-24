import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from sensor_msgs.msg import JointState

import ast

class ArtusROSNode(Node):
    def __init__(self):
        super().__init__('artuslite_ros_node')

        # Setup Parameters
        self._setup_parameters()

        # Initialize Artus API
        self._initialize_artus_api()



        # Connect to the Robot on Node Initialization
        self.artus_api.connect()
        self.get_logger().info("Connected to Artus Hand.")
        # import time
        # time.sleep(5)

        # ----------------------- Control -----------------------
        # Create a subscriber to set joint angles (command topic)
        self.joint_sub = self.create_subscription(JointState, 'artuslite_joint_command', self.set_joint_angles, 10)

        # ----------------------- Feedback -----------------------
        # Create a publisher to publish joint angles (feedback topic)
        if self.feedback == True:
            self.get_logger().info("Publishing joint angles.")
            self.joint_pub = self.create_publisher(JointState, 'artuslite_joint_feedback', 10)
            
            # Setup timer for publishing joint states at the specified communication frequency
            self.create_timer(1.0 / self.communication_frequency, self.publish_joint_angles)

    def _setup_parameters(self):
        # Declare and initialize parameters
        self.declare_parameter('hand_type', 'left')  # 'left' or 'right'
        self.declare_parameter('communication_method', 'UART')  # 'UART' or 'Wi-Fi'
        self.declare_parameter('communication_channel_identifier', '/dev/ttyUSB0')
        self.declare_parameter('communication_frequency', 50)  # In Hz
        self.declare_parameter('wake_up', False)
        self.declare_parameter('calibrate', False)
        self.declare_parameter('reset', False)
        self.declare_parameter('feedback', True)

        # Retrieve parameter values
        self.hand_type = self.get_parameter('hand_type').get_parameter_value().string_value
        self.communication_method = self.get_parameter('communication_method').get_parameter_value().string_value
        self.communication_channel_identifier = self.get_parameter('communication_channel_identifier').get_parameter_value().string_value
        self.communication_frequency = self.get_parameter('communication_frequency').get_parameter_value().integer_value
        self.wake_up = self.get_parameter('wake_up').get_parameter_value().bool_value
        self.calibrate = self.get_parameter('calibrate').get_parameter_value().bool_value
        self.reset = self.get_parameter('reset').get_parameter_value().bool_value
        self.feedback = self.get_parameter('feedback').get_parameter_value().bool_value

    def _initialize_artus_api(self):
        # Initialize the ArtusAPI object
        self.artus_api = ArtusAPI(hand_type=self.hand_type,
                                  communication_method=self.communication_method,
                                  communication_channel_identifier=self.communication_channel_identifier,
                                  communication_frequency=self.communication_frequency,
                                #   awake=self.wake_up,
                                  reset_on_start=self.reset,
                                  stream=self.feedback)

        # Calibrate the end-effector if specified
        if self.calibrate:
            self.artus_api.calibrate()
            self.get_logger().info("End-effector calibrated.")
        
        self.get_logger().info(f"Configured with {self.hand_type} hand and {self.communication_method} communication method.")

    # ----------------------- Control -----------------------

    def set_joint_angles(self, msg: JointState):
        # Convert `position` values to integers if necessary
        joint_angles = [int(angle) for angle in msg.position]
        
        # Prepare hand_joints dictionary with target_angle and velocity for each joint
        hand_joints = {}
        for i in range(16):
            joint = {'index': i, 'target_angle': joint_angles[i], 'velocity': 50}
            hand_joints[i] = joint
        
        # Send command to Artus API
        self.get_logger().info(f"Sending joint angles to Artus API: {hand_joints}")
        self.artus_api.set_joint_angles(joint_angles=hand_joints)

    # ----------------------- Feedback -----------------------
    def publish_joint_angles(self):
        joint_angles = self.artus_api.get_joint_angles()
        # joint_angles = self.decode_message_from_string(joint_angles)
        if joint_angles is None:
            self.get_logger().warning("No joint angles received.")
            return  # Exit early if there's no data to process
        
        position = []
        current = []
        temperature = []
        for name,joint_data in self.artus_api._robot_handler.robot.hand_joints.items():
            position.append(joint_data.feedback_angle)
            current.append(joint_data.feedback_current)
            temperature.append(joint_data.feedback_temperature)

        # conver list elements to float
        position = [float(i) for i in position]
        current = [float(i) for i in current]
        temperature = [float(i) for i in temperature]

        # eg. position feedback: [-1, 0, 0, 0, 0, 0, 0, 16, 0, 0, 15, 0, 0, 0, 0, 0]

        # Publish joint angles
        msg = JointState()
        msg.name = ['thumb1', 'thumb2', 'thumb3', 'thumb4', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3', 'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3']
        msg.position = position
        # msg.velocity = [0] * 16
        # msg.effort = [0] * 16
        self.joint_pub.publish(msg)
     
        # self.joint_pub.publish(joint_angles)
        # self.get_logger().info(f"Published joint angles: {position}")



def main(args=None):
    rclpy.init(args=args)
    artuslite_ros_node = ArtusROSNode()
    rclpy.spin(artuslite_ros_node)
    artuslite_ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

# ros2 topic pub /artuslite_joint_command sensor_msgs/JointState "{name: ['thumb1', 'thumb2', 'thumb3', 'thumb4', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3', 'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3'], position: [10, 20, 15, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]}"
# ros2 topic pub /artuslite_joint_command sensor_msgs/JointState "{name: ['thumb1', 'thumb2', 'thumb3', 'thumb4', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3', 'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3'], position: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}"

