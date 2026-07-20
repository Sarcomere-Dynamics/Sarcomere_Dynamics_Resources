"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Thin ZMQ PUB/SUB wrappers used for topic-based messaging between components."""

import zmq
import time

class ZMQPublisher:
    """Wraps a ZMQ PUB socket for non-blocking, topic-prefixed message broadcast."""

    def __init__(self, address="tcp://127.0.0.1:5556"):
        """Creates the ZMQ context, binds a PUB socket, and waits for subscribers.

        Args:
            address: ZMQ address to bind the PUB socket to.
        """
        # Initialize ZMQ context and PUB socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(address)
        # Allow some time for subscribers to connect
        time.sleep(1)

    def send(self, topic, message):
        """Publishes a message under the given topic, without blocking.

        Args:
            topic: Topic string prefixed to the message for subscriber
                filtering.
            message: Message body to send.
        """
        # Send message with a topic in a non-blocking manner
        try:
            self.socket.send_string(f"{topic} {message}", zmq.NOBLOCK)
        except zmq.ZMQError as e:
            print(f"Send failed: {e}")

    def close(self):
        """Closes the socket and terminates the ZMQ context."""
        self.socket.close()
        self.context.term()

class ZMQSubscriber:
    """Wraps a ZMQ SUB socket configured to keep only the most recent message.

    Uses CONFLATE so that a slow consumer always sees the latest published
    value for its subscribed topics rather than an accumulating backlog.
    """

    def __init__(self, address="tcp://127.0.0.1:5556", topics=None, connect=True):
        """Creates the ZMQ context, sets up a SUB socket, and subscribes to topics.

        Args:
            address: ZMQ address to connect to (or bind, if connect is
                False).
            topics: Iterable of topic strings to subscribe to. Defaults to
                subscribing to all topics when None.
            connect: If True, connects the socket to address; if False,
                binds the socket to address instead.
        """
        # Initialize ZMQ context and SUB socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.CONFLATE, 1) # Only keep the most recent message
        if connect:
            self.socket.connect(address)
        else:
            self.socket.bind(address)

        # Subscribe to specific topics or all topics
        if topics is None:
            topics = [""]
        for topic in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)

    def receive(self):
        """Non-blockingly reads the latest message for the subscribed topics.

        Returns:
            The message body (topic prefix stripped), or None if no
            message is currently available.
        """
        # Non-blocking receive
        try:
            message = self.socket.recv_string(zmq.NOBLOCK)
            # split data into topic and message
            parts = message.split(' ', 1)
            result = [parts[0], parts[1] if len(parts) > 1 else ""]
            # print(f"ZMQ receive: topic={result[0]}, message={result[1]}")
            return result[1]
        except zmq.Again:
            # print("ZMQ error")
            return None

    def close(self):
        """Closes the socket and terminates the ZMQ context."""
        self.socket.close()
        self.context.term()



# Example usage
def publisher_example():
    """Demonstrates ZMQPublisher by sending 30 timestamped messages, one per second."""
    # Publisher
    publisher = ZMQPublisher()

    # Simulate sending messages
    for i in range(30):
        publisher.send("topic1", f"Message {i}")
        time.sleep(1)  # Simulate work

    # Cleanup
    publisher.close()

def subscriber_example():
    """Demonstrates ZMQSubscriber by polling for messages on "topic1" in a loop."""
    # Subscriber
    subscriber = ZMQSubscriber(topics=["topic1"])

    # Simulate receiving messages
    while True:
        received_message = subscriber.receive()
        if received_message:
            None
            # print(f"Received: {received_message}")
        else:
            print("No message available")
            time.sleep(1)  # Simulate work

    # Cleanup
    subscriber.close()

if __name__ == "__main__":
    # publisher_example()
    subscriber_example()
