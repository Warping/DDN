##########################################################
# This RNS example demonstrates broadcasting unencrypted #
# information to any listening destinations.             #
##########################################################

import sys
import argparse
import RNS
import time

class BroadcastHandler:

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
            lambda data, packet : self.packet_buffer.append((time.monotonic(), data, packet))
            )
        
    def get_packet(self):
        if len(self.packet_buffer) > 0:
            return self.packet_buffer.pop(0)
        else:
            return None
        
    def send_broadcast(self, data):
        packet = RNS.Packet(self.broadcast_destination, data)
        return packet.send()

