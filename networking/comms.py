class Comms:
    def __init__(self):
        self.connections = []

    def connect(self, address):
        # Placeholder for connection logic
        self.connections.append(address)
        print(f"Connected to {address}")

    def disconnect(self, address):
        # Placeholder for disconnection logic
        if address in self.connections:
            self.connections.remove(address)
            print(f"Disconnected from {address}")
        else:
            print(f"No connection found for {address}")

    def send(self, address, message):
        # Placeholder for sending message logic
        if address in self.connections:
            print(f"Sending message to {address}: {message}")
        else:
            print(f"Cannot send message. No connection to {address}")

    def receive(self):
        # Placeholder for receiving message logic
        print("Receiving messages...")
        # Simulate receiving a message
        return "Sample message received"