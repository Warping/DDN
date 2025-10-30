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
    
    def discovery_announce(self, bh : BroadcastHandler, drone_id, current_state, position, battery_level=100.0, capabilities=None):
        """Announce this drone's presence and capabilities to the network"""
        params = {
            "position": position,
            "battery_level": battery_level,
            "capabilities": capabilities if capabilities else [],
            "discovery_time": time.time()
        }
        self.command(bh, drone_id, -1, current_state, "DISCOVERY_ANNOUNCE", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def discovery_response(self, bh : BroadcastHandler, drone_id, destination_id, current_state, position, battery_level=100.0, capabilities=None):
        """Respond to a discovery announcement"""
        params = {
            "position": position,
            "battery_level": battery_level,
            "capabilities": capabilities if capabilities else [],
            "response_time": time.time()
        }
        self.command(bh, drone_id, destination_id, current_state, "DISCOVERY_RESPONSE", params)
        return bh.send_broadcast(self.to_json().encode('utf-8'))
    
    def heartbeat(self, bh : BroadcastHandler, drone_id, current_state, position, battery_level=100.0):
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
        # Check if we're receiving a comprehensive network state dictionary
        if isinstance(known_drones, dict) and 'drones_by_role' in known_drones:
            # Create a compact version with only essential information
            compact_drones = []
            all_drones = known_drones['drones_by_role']['masters'] + \
                         known_drones['drones_by_role']['slaves'] + \
                         known_drones['drones_by_role']['connected'] + \
                         known_drones['drones_by_role']['seeking'] + \
                         known_drones['drones_by_role']['offline']
            for drone in all_drones:
                compact_drone = {
                    "id": drone.get('drone_id'),
                    "st": drone.get('status'),
                    "pos": drone.get('position'),
                    "bat": drone.get('battery_level', 100.0),
                    "sig": drone.get('signal_strength', 0.0)
                }
                compact_drones.append(compact_drone)
            
            params = {
                "compact_state": True,
                "drones": compact_drones,
                "master_id": master_id,
                "status_time": time.time()
            }
        else:
            # Original format for backward compatibility
            params = {
                "known_drones": known_drones if known_drones else [],
                "master_id": master_id,
                "status_time": time.time()
            }
        
        self.command(bh, drone_id, -1, current_state, "NETWORK_STATUS", params)
        
        # Check packet size before sending
        packet_json = self.to_json()
        packet_size = len(packet_json.encode('utf-8'))
        max_size = 480  # Slightly below the 500 MTU to allow for headers
        
        if packet_size > max_size:
            # If still too large, create an optimized format with positions
            print(f"⚠️ Network status packet size ({packet_size} bytes) exceeds limit. Creating optimized format.")
            
            # We need to reduce the data further but keep positions
            # 1. Use short keys (p=position, i=id)
            # 2. Round position values to 1 decimal place to reduce size
            # 3. Split into batches if needed
            
            optimized_drones = []
            if "compact_state" in params and "drones" in params:
                # Create highly optimized version with just ID and rounded positions
                for drone in params["drones"]:
                    pos = drone["pos"]
                    # Round position to 1 decimal place to reduce size
                    rounded_pos = [round(p, 1) for p in pos]
                    optimized_drones.append({
                        "i": drone["id"],
                        "p": rounded_pos
                    })
            
            # Check if we have too many drones - if so, send in batches
            # Estimate ~45 bytes per drone entry (id + position)
            max_drones_per_packet = 8  # Very conservative estimate to ensure we're under MTU
            
            if len(optimized_drones) > max_drones_per_packet:
                print(f"⚠️ Too many drones ({len(optimized_drones)}) for a single packet. Sending first {max_drones_per_packet} only.")
                # Just take the first batch - in a real implementation, you might want to send multiple packets
                optimized_drones = optimized_drones[:max_drones_per_packet]
                
            # Further optimize by removing any unnecessary data
            # Float precision can be further reduced if needed
            for drone in optimized_drones:
                pos = drone["p"]
                # Round position to 1 decimal place to reduce size - keep only one decimal for even more space savings
                drone["p"] = [int(p*10)/10 for p in pos]
            
            minimal_params = {
                "opt": True,  # optimized format indicator
                "d": optimized_drones,
                "m": master_id,
                "t": int(time.time())  # Integer timestamp saves space
            }
            
            self.command(bh, drone_id, -1, current_state, "NETWORK_STATUS", minimal_params)
        
        # Only send if we have a broadcast handler (for testing purposes)
        if bh:
            return bh.send_broadcast(self.to_json().encode('utf-8'))
        return self.to_json().encode('utf-8')  # Return encoded data for testing
    
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
    