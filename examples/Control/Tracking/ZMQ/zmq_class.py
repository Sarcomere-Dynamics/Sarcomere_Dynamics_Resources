import zmq
import time

class ZMQPublisher:
    def __init__(self, address="tcp://127.0.0.1:5556"):
        # Initialize ZMQ context and PUB socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(address)
        # Allow some time for subscribers to connect
        time.sleep(1)

    def send(self, topic, message):
        # Send message with a topic in a non-blocking manner
        try:
            self.socket.send_string(f"{message}", zmq.NOBLOCK)
        except zmq.ZMQError as e:
            print(f"Send failed: {e}")

    def close(self):
        self.socket.close()
        self.context.term()


class ZMQSubscriber:
    def __init__(self, address="tcp://127.0.0.1:5556", topics=None):
        # Initialize ZMQ context and SUB socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.CONFLATE, 1) # Only keep the most recent message
        self.socket.connect(address)
        # Subscribe to specific topics or all topics
        if topics is None:
            topics = [""]
        for topic in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)

    def receive(self):
        # Non-blocking receive
        try:
            message = self.socket.recv_string(zmq.NOBLOCK)
            return message
        except zmq.Again:
            return None

    def close(self):
        self.socket.close()
        self.context.term()


# Example usage
def publisher_example():
    # Publisher
    publisher = ZMQPublisher()

    # Simulate sending messages
    for i in range(10):
        publisher.send("topic1", f"Message {i}")
        time.sleep(1)  # Simulate work

    # Cleanup
    publisher.close()

def subscriber_example():
    # Subscriber
    subscriber = ZMQSubscriber(topics=["topic1"])

    # Simulate receiving messages
    while True:
        received_message = subscriber.receive()
        if received_message:
            print(f"Received: {received_message}")
        else:
            print("No message available")
            time.sleep(1)  # Simulate work

    # Cleanup
    subscriber.close()

if __name__ == "__main__":
    publisher_example()
    # subscriber_example()
