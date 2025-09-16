import json
import time
from broadcast_controller import BroadcastHandler

class DronePacket:
    def __init__(self, json_string=None):
        if json_string:
            self.decode_json(json_string)

    def to_json(self):
        packet = {
            "timestamp": self.timestamp,
            "drone_id": self.drone_id,
            "destination_id": self.destination_id,
            "current_state": self.current_state,
            "action": self.request_action,
            "params": self.params
        }
        return json.dumps(packet)
    
    def decode_json(self, json_string):
        packet = json.loads(json_string)
        self.timestamp = packet.get("timestamp", None)
        self.drone_id = packet.get("drone_id", None)
        self.destination_id = packet.get("destination_id", None)
        self.current_state = packet.get("current_state", None)
        self.request_action = packet.get("action", None)
        self.params = packet.get("params", {})
        
    def command(self, bh : BroadcastHandler, drone_id, destination_id, current_state, command, params):
        self.timestamp = time.monotonic()
        self.drone_id = drone_id
        self.destination_id = destination_id
        self.current_state = current_state
        self.request_action = command
        self.params = params
        # return bh.send_broadcast(self.to_json().encode('utf-8'))

    def ping(self, bh : BroadcastHandler, drone_id, destination_id, current_state):
        self.command(bh, drone_id, destination_id, current_state, "PING", {})
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def set_slave(self, bh : BroadcastHandler, drone_id, destination_id, current_state):
        self.command(bh, drone_id, destination_id, current_state, "SET_SLAVE", {})
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def set_id(self, bh : BroadcastHandler, drone_id, destination_id, current_state, new_id):
        self.command(bh, drone_id, destination_id, current_state, "SET_ID", {"new_id": new_id})
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def update(self, bh : BroadcastHandler, drone_id, destination_id, current_state, update_info=None):
        self.command(bh, drone_id, destination_id, current_state, "UPDATE", update_info if update_info else {})
        return bh.send_broadcast(self.to_json().encode('utf-8'))

    def ack(self, bh : BroadcastHandler, drone_id, destination_id, current_state, ack_info=None):
        self.command(bh, drone_id, destination_id, current_state, "ACK", ack_info if ack_info else {})
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    