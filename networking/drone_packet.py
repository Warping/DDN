import json
import time
from networking.broadcast_controller import BroadcastHandler

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
    
    def discovery_announce(self, bh : BroadcastHandler, drone_id, current_state, position=(0,0,0), battery_level=100.0, capabilities=None):
        """Announce this drone's presence and capabilities to the network"""
        params = {
            "position": position,
            "battery_level": battery_level,
            "capabilities": capabilities if capabilities else [],
            "discovery_time": time.time()
        }
        self.command(bh, drone_id, -1, current_state, "DISCOVERY_ANNOUNCE", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def discovery_response(self, bh : BroadcastHandler, drone_id, destination_id, current_state, position=(0,0,0), battery_level=100.0, capabilities=None):
        """Respond to a discovery announcement"""
        params = {
            "position": position,
            "battery_level": battery_level,
            "capabilities": capabilities if capabilities else [],
            "response_time": time.time()
        }
        self.command(bh, drone_id, destination_id, current_state, "DISCOVERY_RESPONSE", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def heartbeat(self, bh : BroadcastHandler, drone_id, current_state, position=(0,0,0), battery_level=100.0):
        """Send heartbeat to maintain network presence"""
        params = {
            "position": position,
            "battery_level": battery_level,
            "heartbeat_time": time.time()
        }
        self.command(bh, drone_id, -1, current_state, "HEARTBEAT", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def network_status(self, bh : BroadcastHandler, drone_id, current_state, known_drones=None, master_id=None):
        """Share network topology information"""
        params = {
            "known_drones": known_drones if known_drones else [],
            "master_id": master_id,
            "status_time": time.time()
        }
        self.command(bh, drone_id, -1, current_state, "NETWORK_STATUS", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def id_conflict_resolution(self, bh : BroadcastHandler, drone_id, destination_id, current_state, old_id, new_id):
        """Announce ID conflict resolution"""
        params = {
            "old_id": old_id,
            "new_id": new_id,
            "resolution_time": time.time()
        }
        self.command(bh, drone_id, destination_id, current_state, "ID_CONFLICT_RESOLUTION", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def elect_master(self, bh : BroadcastHandler, drone_id, current_state, candidate_id, criteria=None):
        """Participate in master election process"""
        params = {
            "candidate_id": candidate_id,
            "criteria": criteria if criteria else {},
            "election_time": time.time()
        }
        self.command(bh, drone_id, -1, current_state, "ELECT_MASTER", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    