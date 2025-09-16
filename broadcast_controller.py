import RNS
import time

class BroadcastHandler:
    """
    BroadcastHandler provides a simple interface for broadcasting and receiving messages
    using Reticulum's PLAIN destination. It manages a buffer of received packets and
    allows sending broadcast messages to all listeners.
    Attributes:
        packet_buffer (list): Stores tuples of (timestamp, data, packet) for received packets.
        broadcast_destination (RNS.Destination): The Reticulum destination for broadcasting.
    Args:
        configpath (str): Path to the Reticulum configuration file. Defaults to "./.reticulum_config".
    Methods:
        get_packet():
            Retrieves and removes the oldest received packet from the buffer.
            Returns:
                tuple or None: (timestamp, data, packet) if available, otherwise None.
        send_broadcast(data):
            Sends a broadcast message with the given data to all listeners.
            Args:
                data (bytes): The data to broadcast.
            Returns:
                bool: True if the packet was sent successfully, False otherwise.
    Usage example:
        handler = BroadcastHandler()
        handler.send_broadcast(b"Hello, world!")
        packet = handler.get_packet()
        if packet:
            timestamp, data, packet_obj = packet
            print("Received:", data)
    """
    
    
    # This initialisation is executed when the program is started
    def __init__(self, configpath="./.reticulum_config"):
        # We must first initialise Reticulum
        self.packet_buffer = []
        _ = RNS.Reticulum(configpath)

        # We create a PLAIN destination. This is an uncencrypted endpoint
        # that anyone can listen to and send information to.
        self.broadcast_destination = RNS.Destination(
            None,
            RNS.Destination.IN,
            RNS.Destination.PLAIN,
            "example_utilities",
            "broadcast",
            "public_information"
        )

        # We specify a callback that will get called every time
        # the destination receives data.
        self.broadcast_destination.set_packet_callback(
            lambda data, packet : self.packet_buffer.append((time.monotonic_ns(), data, packet))
            )
        
    def get_packet(self):
        if len(self.packet_buffer) > 0:
            return self.packet_buffer.pop(0)
        else:
            return None
        
    def send_broadcast(self, data):
        packet = RNS.Packet(self.broadcast_destination, data, create_receipt=True)
        return packet.send()

