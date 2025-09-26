import time
import random
import os
import sys

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from networking.broadcast_controller import BroadcastHandler
from networking.drone_packet import DronePacket
from core.drone_state import DroneNetwork, DroneStatus

class EnhancedStateController:
    """
    Enhanced state controller that uses the comprehensive drone state management system.
    Handles network discovery, ID conflict resolution, and maintains network topology.
    """
    
    def __init__(self, drone_id=None, quiet_mode=False):
        self.drone_network = DroneNetwork(drone_id)
        self.bh = BroadcastHandler()
        self.time_step = 0.5  # Base time step in seconds - increased from 3.0
        self.discovery_interval = 5.0  # Discovery announcement interval - increased from 5.0
        self.heartbeat_interval = 10.0  # Heartbeat interval - increased from 10.0
        self.network_sync_interval = 15.0  # Network status sharing interval - increased from 15.0
        self.master_election_interval = 8.0  # Master election check interval - increased from 8.0
        self.master_timeout = 25.0  # Time to wait before considering master offline - reduced from 25.0
        self.quiet_mode = quiet_mode  # Suppress frequent status messages
        
        # Update intervals to be proportional to time_step
        self.discovery_interval *= self.time_step
        self.heartbeat_interval *= self.time_step
        self.network_sync_interval *= self.time_step
        self.master_election_interval *= self.time_step
        self.master_timeout *= self.time_step
        
        # Timing variables
        self.last_discovery_time = 0
        self.last_heartbeat_time = 0
        self.last_network_sync_time = 0
        self.last_cleanup_time = 0
        self.last_status_display_time = 0  # Add this to prevent spam
        self.last_master_check_time = 0  # Master election check timing
        self.last_master_heartbeat_time = 0  # Last time we heard from master
        
        # State management
        self.discovery_attempts = 0
        self.max_discovery_attempts = 10
        self.network_stable_time = 0
        self.min_stable_time = 15.0 * self.time_step # Reduced from 15s for faster elections
        
        # Master election state
        self.election_in_progress = False
        self.election_start_time = 0
        self.election_timeout = 10.0 * self.time_step # Election must complete within 5 seconds - reduced from 10.0
        self.election_votes = {}  # Track votes during election
        self.has_voted = False
        
        print(f"Enhanced State Controller initialized with drone ID: {self.drone_network.get_self_id()}")
    
    def process_incoming_packets(self):
        """Process all incoming packets and update network state"""
        while True:
            packet_data = self.bh.get_packet()
            if packet_data is None:
                break
                
            timestamp_ns, data, rns_packet = packet_data
            
            # # Decode the packet
            # drone_packet = DronePacket(data.decode('utf-8'))
            # self.handle_received_packet(drone_packet)
            
            try:
                # Decode the packet
                drone_packet = DronePacket(data.decode('utf-8'))
                self.handle_received_packet(drone_packet)
                
            except Exception as e:
                print(f"Error processing packet: {e}")
                continue
    
    def handle_received_packet(self, packet: DronePacket):
        """Handle different types of received packets"""
        sender_id = packet.drone_id
        action = packet.request_action
        params = packet.params
        
        # Ignore packets from ourselves
        if sender_id == self.drone_network.get_self_id():
            return
        
        # Check for ID conflicts
        if self.drone_network.detect_id_conflict(sender_id, sender_id):
            print(f"ID conflict detected with drone {sender_id}")
            new_id = self.drone_network.resolve_id_conflict()
            # Announce the resolution
            DronePacket().id_conflict_resolution(
                self.bh, new_id, -1, self.drone_network.self_drone.status.value, 
                sender_id, new_id
            )
            return
        
        # Update or add the sender drone
        position = params.get("position", None)  # Don't default to (0,0,0)
        battery_level = params.get("battery_level", None)
        signal_strength = params.get("signal_strength", None)
        
        # Only update position if it's provided in the packet
        if position is not None and battery_level is not None and signal_strength is not None:
            sender_drone = self.drone_network.add_or_update_drone(
                sender_id, DroneStatus(packet.current_state), 
                position, battery_level, signal_strength
            )
        else:
            # Update without changing position
            if sender_id in self.drone_network.known_drones:
                sender_drone = self.drone_network.known_drones[sender_id]
                sender_drone.status = DroneStatus(packet.current_state)
                # sender_drone.update_battery(battery_level)
                # sender_drone.signal_strength = signal_strength
                sender_drone.update_last_seen()
            else:
                # New drone without position - let it keep its random initial position
                sender_drone = self.drone_network.add_or_update_drone(
                    sender_id, DroneStatus(packet.current_state)
                )
        
        # Handle specific packet types
        if action == "PING":
            self.handle_ping(packet)
        elif action == "DISCOVERY_ANNOUNCE":
            self.handle_discovery_announce(packet)
        elif action == "DISCOVERY_RESPONSE":
            self.handle_discovery_response(packet)
        elif action == "HEARTBEAT":
            self.handle_heartbeat(packet)
        elif action == "NETWORK_STATUS":
            self.handle_network_status(packet)
        elif action == "ID_CONFLICT_RESOLUTION":
            self.handle_id_conflict_resolution(packet)
        elif action == "ELECT_MASTER":
            self.handle_master_election(packet)
        elif action == "ACK":
            self.handle_ack(packet)
        
        # Update network status after processing
        self.drone_network.update_network_status()
    
    def handle_ping(self, packet: DronePacket):
        """Handle ping packets"""
        sender_id = packet.drone_id
        
        # Respond with our current state
        DronePacket().ack(
            self.bh, self.drone_network.get_self_id(), sender_id,
            self.drone_network.self_drone.status.value,
            {
                "position": self.drone_network.self_drone.position,
                "battery_level": self.drone_network.self_drone.battery_level,
                "ping_response": True
            }
        )
        
        print(f"Responded to ping from drone {sender_id}")
    
    def handle_discovery_announce(self, packet: DronePacket):
        """Handle discovery announcement packets"""
        sender_id = packet.drone_id
        
        # Respond to discovery announcement
        DronePacket().discovery_response(
            self.bh, self.drone_network.get_self_id(), sender_id,
            self.drone_network.self_drone.status.value,
            self.drone_network.self_drone.position,
            self.drone_network.self_drone.battery_level,
            self.drone_network.self_drone.capabilities
        )
        
        print(f"Responded to discovery announcement from drone {sender_id}")
    
    def handle_discovery_response(self, packet: DronePacket):
        """Handle discovery response packets"""
        sender_id = packet.drone_id
        print(f"Received discovery response from drone {sender_id}")
        
        # Update drone capabilities if provided
        if "capabilities" in packet.params:
            sender_drone = self.drone_network.get_drone(sender_id)
            if sender_drone:
                sender_drone.capabilities = packet.params["capabilities"]
    
    def handle_heartbeat(self, packet: DronePacket):
        """Handle heartbeat packets"""
        sender_id = packet.drone_id
        
        if not self.quiet_mode:
            print(f"Received heartbeat from drone {sender_id}")
        
        # If this heartbeat is from the current master, update master heartbeat time
        if sender_id == self.drone_network.master_drone_id:
            self.last_master_heartbeat_time = time.time()
            if not self.quiet_mode:
                print(f"📡 Updated master heartbeat time for master {sender_id}")
        
        # Update the sender's last_seen time through add_or_update_drone
        # This is already handled in handle_received_packet, but let's ensure it's updated
        sender_drone = self.drone_network.get_drone(sender_id)
        if sender_drone:
            sender_drone.update_last_seen()
        
        # If we receive a heartbeat from a drone claiming to be master, but we think someone else is master
        sender_status = packet.params.get('status', 'unknown')
        if (sender_status == 'master' and 
            self.drone_network.master_drone_id and 
            self.drone_network.master_drone_id != sender_id):
            
            print(f"⚠️ Conflicting master claim: {sender_id} claims master but we think {self.drone_network.master_drone_id} is master")
            # Trigger re-election to resolve conflict
            if not self.election_in_progress:
                print("🗳️ Starting election to resolve master conflict")
                self.drone_network.master_drone_id = None  # Clear conflicting master
                self.initiate_master_election()
    
    def handle_network_status(self, packet: DronePacket):
        """Handle network status sharing packets"""
        sender_id = packet.drone_id
        known_drones = packet.params.get("known_drones", [])
        master_id = packet.params.get("master_id")
        
        if not self.quiet_mode:
            print(f"Received network status from drone {sender_id}: {len(known_drones)} known drones, master: {master_id}")
        
        # Update our knowledge of the network
        for drone_info in known_drones:
            if drone_info != self.drone_network.get_self_id():
                # Only add new drones or update status, don't change position without position data
                if drone_info not in self.drone_network.known_drones:
                    # New drone - add it with default status
                    self.drone_network.add_or_update_drone(drone_info, DroneStatus.CONNECTED)
                else:
                    # Existing drone - just update status and timestamp, preserve position
                    existing_drone = self.drone_network.known_drones[drone_info]
                    existing_drone.status = DroneStatus.CONNECTED
                    existing_drone.update_last_seen()
        
        # Update master information if provided
        if master_id and master_id != self.drone_network.master_drone_id:
            if not self.quiet_mode:
                print(f"Network status indicates master is {master_id}")
            self.drone_network.master_drone_id = master_id
            self.last_master_heartbeat_time = time.time()
    
    def share_network_status(self):
        """Share our view of the network with other drones"""
        online_drones = self.drone_network.get_online_drones()
        known_drone_ids = [drone.drone_id for drone in online_drones]
        
        # Include ourselves in the list
        if self.drone_network.get_self_id() not in known_drone_ids:
            known_drone_ids.append(self.drone_network.get_self_id())
        
        packet = DronePacket()
        packet.network_status(
            self.bh,
            self.drone_network.get_self_id(),
            self.drone_network.self_drone.status.value,
            known_drone_ids,
            self.drone_network.master_drone_id
        )
        
        if not self.quiet_mode:
            print(f"Shared network status: {len(known_drone_ids)} drones, master: {self.drone_network.master_drone_id}")
    
    def handle_id_conflict_resolution(self, packet: DronePacket):
        """Handle ID conflict resolution announcements"""
        old_id = packet.params.get("old_id")
        new_id = packet.params.get("new_id")
        
        print(f"Drone resolved ID conflict: {old_id} -> {new_id}")
        
        # Update our records if we know about the old ID
        if old_id in self.drone_network.known_drones:
            old_drone = self.drone_network.known_drones[old_id]
            del self.drone_network.known_drones[old_id]
            old_drone.drone_id = new_id
            self.drone_network.known_drones[new_id] = old_drone
    
    def handle_master_election(self, packet: DronePacket):
        """Handle master election packets"""
        sender_id = packet.drone_id
        candidate_id = packet.params.get("candidate_id", sender_id)
        criteria = packet.params.get("criteria", {})
        
        if not self.quiet_mode:
            print(f"Master election: drone {candidate_id} proposed by {sender_id}")
        
        # If we're not in an election, ignore this
        if not self.election_in_progress:
            if not self.quiet_mode:
                print("Ignoring election packet - no election in progress")
            return
        
        # Record the vote
        self.election_votes[sender_id] = candidate_id
        
        # Check if we should vote too
        if not self.has_voted:
            self.participate_in_election()
    
    def initiate_master_election(self):
        """Initiate a new master election"""
        if self.election_in_progress:
            return  # Election already in progress
        
        self.election_in_progress = True
        self.election_start_time = time.time()
        self.election_votes = {}
        self.has_voted = False
        
        print(f"🗳️  Initiating master election - current master offline or missing")
        
        # Participate in the election immediately
        self.participate_in_election()
    
    def participate_in_election(self):
        """Participate in ongoing master election"""
        if self.has_voted:
            return
        
        # Determine our preferred candidate (could be ourselves)
        candidate_id = self.select_master_candidate()
        
        # Calculate election criteria for our candidate
        criteria = self.calculate_election_criteria(candidate_id)
        
        # Send our vote
        packet = DronePacket()
        packet.elect_master(
            self.bh,
            self.drone_network.get_self_id(),
            self.drone_network.self_drone.status.value,
            candidate_id,
            criteria
        )
        
        self.has_voted = True
        self.election_votes[self.drone_network.get_self_id()] = candidate_id
        
        if not self.quiet_mode:
            print(f"Voted for drone {candidate_id} as master")
    
    def select_master_candidate(self):
        """Select the best candidate for master based on criteria"""
        online_drones = self.drone_network.get_online_drones()
        
        if not online_drones:
            return self.drone_network.get_self_id()
        
        # Election criteria (in order of priority):
        # 1. Highest battery level
        # 2. Lowest drone ID (tie breaker)
        # 3. Longest uptime
        
        best_candidate = None
        best_score = (-1, float('inf'), -1)  # (battery, -drone_id, -uptime)
        
        for drone in online_drones:
            uptime = time.time() - drone.discovery_time
            score = (drone.battery_level, -drone.drone_id, uptime)
            
            if score > best_score:
                best_score = score
                best_candidate = drone.drone_id
        
        # Consider ourselves as well
        self_uptime = time.time() - self.drone_network.self_drone.discovery_time
        self_score = (
            self.drone_network.self_drone.battery_level,
            -self.drone_network.get_self_id(),
            self_uptime
        )
        
        if self_score > best_score:
            best_candidate = self.drone_network.get_self_id()
        
        return best_candidate if best_candidate else self.drone_network.get_self_id()
    
    def calculate_election_criteria(self, candidate_id):
        """Calculate election criteria for a candidate"""
        if candidate_id == self.drone_network.get_self_id():
            drone = self.drone_network.self_drone
        else:
            drone = self.drone_network.get_drone(candidate_id)
        
        if not drone:
            return {"battery_level": 0, "uptime": 0, "reliability": 0}
        
        uptime = time.time() - drone.discovery_time
        reliability = drone.get_reliability_score()
        
        return {
            "battery_level": drone.battery_level,
            "uptime": uptime,
            "reliability": reliability,
            "drone_id": candidate_id  # Lower ID is better (tie breaker)
        }
    
    def process_election_results(self):
        """Process election results and determine winner"""
        if not self.election_in_progress:
            return
        
        # Check if election has timed out
        if time.time() - self.election_start_time > self.election_timeout:
            self.finalize_election()
    
    def finalize_election(self):
        """Finalize the election and announce results"""
        if not self.election_in_progress:
            return
        
        # Count votes
        vote_counts = {}
        for voter, candidate in self.election_votes.items():
            vote_counts[candidate] = vote_counts.get(candidate, 0) + 1
        
        if not vote_counts:
            # No votes received, elect ourselves
            winner = self.drone_network.get_self_id()
        else:
            # Winner is candidate with most votes, lowest ID breaks ties
            winner = min(vote_counts.keys(), key=lambda x: (-vote_counts[x], x))
        
        # Update network state
        old_master = self.drone_network.master_drone_id
        self.drone_network.master_drone_id = winner
        
        # Update drone statuses
        online_drones = self.drone_network.get_online_drones()
        for drone in online_drones:
            if drone.drone_id == winner:
                drone.status = DroneStatus.MASTER
            else:
                drone.status = DroneStatus.SLAVE
        
        # Update our own status
        if winner == self.drone_network.get_self_id():
            self.drone_network.self_drone.status = DroneStatus.MASTER
            print(f"👑 Elected as MASTER drone (received {vote_counts.get(winner, 1)} votes)")
        else:
            self.drone_network.self_drone.status = DroneStatus.SLAVE
            print(f"🤝 Drone {winner} elected as MASTER (received {vote_counts.get(winner, 1)} votes)")
        
        # Reset election state
        self.election_in_progress = False
        self.election_votes = {}
        self.has_voted = False
        self.last_master_heartbeat_time = time.time()
        
        # Announce new master to network
        self.share_network_status()
    
    def check_master_status(self):
        """Check if master is still alive and trigger re-election if needed"""
        current_time = time.time()
        
        # Skip check if we just completed an election
        if current_time - self.last_master_check_time < self.master_election_interval:
            return
        
        self.last_master_check_time = current_time
        
        # If no master assigned and network is stable, start election
        if (self.drone_network.master_drone_id is None and 
            self.drone_network.get_online_drone_count() > 1 and
            not self.election_in_progress):
            print("No master assigned - initiating election")
            self.initiate_master_election()
            return
        
        # Check if current master is still online
        if self.drone_network.master_drone_id:
            master_drone = self.drone_network.get_drone(self.drone_network.master_drone_id)
            
            # Multiple conditions to detect master death:
            # 1. Master drone not found in our known drones
            # 2. Master drone marked as not online (using is_online check)
            # 3. Haven't received heartbeat from master in timeout period
            master_offline = False
            offline_reason = ""
            
            if not master_drone:
                master_offline = True
                offline_reason = "master not found in known drones"
            elif not master_drone.is_online(self.master_timeout):
                master_offline = True
                offline_reason = f"master last seen {current_time - master_drone.last_seen:.1f}s ago"
            elif (current_time - self.last_master_heartbeat_time > self.master_timeout):
                master_offline = True
                offline_reason = f"no master heartbeat for {current_time - self.last_master_heartbeat_time:.1f}s"
            
            # If we are master, ignore offline checks
            if self.drone_network.self_drone.status == DroneStatus.MASTER:
                master_offline = False
            
            
            if master_offline:
                print(f"💀 Master drone {self.drone_network.master_drone_id} is offline ({offline_reason}) - initiating re-election")
                
                # Clear the dead master
                old_master_id = self.drone_network.master_drone_id
                self.drone_network.master_drone_id = None
                
                # Remove dead master from known drones if it's really gone
                if master_drone and not master_drone.is_online(self.master_timeout):
                    print(f"🗑️ Removing dead master {old_master_id} from known drones")
                    self.drone_network.remove_drone(old_master_id)
                
                # Start re-election if we have other drones
                if (self.drone_network.get_online_drone_count() >= 1 and 
                    not self.election_in_progress):
                    self.initiate_master_election()
                else:
                    print("No other drones available for re-election")
    
    def handle_ack(self, packet: DronePacket):
        """Handle acknowledgment packets"""
        sender_id = packet.drone_id
        
        # Update response count for reliability tracking
        sender_drone = self.drone_network.get_drone(sender_id)
        if sender_drone:
            sender_drone.increment_response()
    
    def send_discovery_announcement(self):
        """Send discovery announcement to find other drones"""
        DronePacket().discovery_announce(
            self.bh, self.drone_network.get_self_id(),
            self.drone_network.self_drone.status.value,
            self.drone_network.self_drone.position,
            self.drone_network.self_drone.battery_level,
            self.drone_network.self_drone.capabilities
        )
        
        self.discovery_attempts += 1
        print(f"Sent discovery announcement (attempt {self.discovery_attempts})")
    
    def send_heartbeat(self):
        """Send heartbeat to maintain network presence"""
        DronePacket().heartbeat(
            self.bh, self.drone_network.get_self_id(),
            self.drone_network.self_drone.status.value,
            self.drone_network.self_drone.position,
            self.drone_network.self_drone.battery_level
        )
        
        print(f"Sent heartbeat")
    
    def send_network_status(self):
        """Share network topology with other drones"""
        known_drone_ids = list(self.drone_network.known_drones.keys())
        
        DronePacket().network_status(
            self.bh, self.drone_network.get_self_id(),
            self.drone_network.self_drone.status.value,
            known_drone_ids,
            self.drone_network.master_drone_id
        )
        
        print(f"Shared network status: {len(known_drone_ids)} known drones")
    
    def update_state_based_on_network(self):
        """Update drone state based on current network conditions"""
        online_drones = self.drone_network.get_online_drones()
        online_count = len(online_drones)
        
        current_status = self.drone_network.self_drone.status
        
        if online_count == 1:  # Only this drone is online
            if current_status != DroneStatus.SEEKING:
                self.drone_network.set_self_status(DroneStatus.SEEKING)
                self.discovery_attempts = 0
                self.network_stable_time = 0
                self.drone_network.master_drone_id = None  # Reset master when alone
                if not self.quiet_mode:
                    print("No other drones detected, switching to SEEKING state")
                
        elif online_count > 1:  # Network exists
            if current_status == DroneStatus.SEEKING:
                self.drone_network.set_self_status(DroneStatus.CONNECTED)
                self.network_stable_time = time.time()
                if not self.quiet_mode:
                    print(f"Connected to network with {online_count} drones")
            
            # Check master status and trigger elections if needed
            self.check_master_status()
            
            # Process ongoing elections
            self.process_election_results()
            
            # Update network status based on master election results
            self.drone_network.update_network_status()
    
    def control_loop(self):
        """Main control loop for enhanced state management"""
        print("Starting enhanced control loop...")
        
        while True:
            current_time = time.time()
            
            # Process incoming packets
            self.process_incoming_packets()
            
            # Send discovery announcements when seeking
            if (self.drone_network.self_drone.status == DroneStatus.SEEKING and
                current_time - self.last_discovery_time > self.discovery_interval and
                self.discovery_attempts < self.max_discovery_attempts):
                
                self.send_discovery_announcement()
                self.last_discovery_time = current_time
            
            # Send periodic heartbeats when connected
            if (self.drone_network.self_drone.status in [DroneStatus.CONNECTED, DroneStatus.MASTER, DroneStatus.SLAVE] and
                current_time - self.last_heartbeat_time > self.heartbeat_interval):
                
                self.send_heartbeat()
                self.last_heartbeat_time = current_time
            
            # Share network status periodically
            if (self.drone_network.network_established and
                current_time - self.last_network_sync_time > self.network_sync_interval):
                
                self.send_network_status()
                self.last_network_sync_time = current_time
            
            # Cleanup offline drones more frequently to detect master death faster
            if current_time - self.last_cleanup_time > 15.0:  # Every 15 seconds instead of 60
                initial_count = self.drone_network.get_drone_count()
                self.drone_network.cleanup_offline_drones(timeout=self.master_timeout)
                final_count = self.drone_network.get_drone_count()
                
                if final_count < initial_count:
                    removed_count = initial_count - final_count
                    print(f"🗑️ Cleaned up {removed_count} offline drones")
                    
                    # If master was removed during cleanup, trigger re-election
                    if (self.drone_network.master_drone_id and 
                        not self.drone_network.get_drone(self.drone_network.master_drone_id)):
                        print(f"💀 Master {self.drone_network.master_drone_id} was cleaned up - clearing master")
                        self.drone_network.master_drone_id = None
                
                self.last_cleanup_time = current_time
            
            # Update state based on network conditions
            self.update_state_based_on_network()
            
            # Display status periodically (every 10 seconds, but only once per interval)
            # Skip frequent displays in quiet mode
            if not self.quiet_mode and current_time - self.last_status_display_time > 10.0:
                self.display_status()
                self.last_status_display_time = current_time
            
            # Sleep to prevent excessive CPU usage
            time.sleep(0.1)
    
    def display_status(self):
        """Display current network status"""
        status = self.drone_network.get_discovery_status()
        online_count = self.drone_network.get_online_drone_count()
        total_count = self.drone_network.get_drone_count()
        
        print(f"\n=== Drone Network Status ===")
        print(f"Self ID: {self.drone_network.get_self_id()}")
        print(f"Status: {self.drone_network.self_drone.status.value}")
        print(f"Network: {status}")
        print(f"Drones: {online_count} online, {total_count} total")
        if self.drone_network.master_drone_id:
            print(f"Master: {self.drone_network.master_drone_id}")
        print("============================\n")
    
    def display_detailed_network(self):
        """Display detailed network visualization"""
        print("\n" + "="*60)
        print("🚁 DETAILED DRONE NETWORK VISUALIZATION 🚁")
        print("="*60)
        
        # Network overview
        online_count = self.drone_network.get_online_drone_count()
        total_count = self.drone_network.get_drone_count()
        
        print(f"📊 Network Status: {self.drone_network.get_discovery_status()}")
        print(f"🌐 Total Drones: {total_count} | Online: {online_count}")
        print(f"🆔 Self ID: {self.drone_network.get_self_id()}")
        
        if self.drone_network.master_drone_id:
            print(f"👑 Master: {self.drone_network.master_drone_id}")
        else:
            print("👑 Master: None")
        
        print("-" * 60)
        
        # Drone details table
        drones = self.drone_network.get_all_drones()
        if drones:
            print(f"{'ID':>6} {'Status':>10} {'Position':>20} {'Battery':>10} {'Age':>8}")
            print("-" * 60)
            
            for drone in sorted(drones, key=lambda d: d.drone_id):
                # Status with emoji
                status_symbols = {
                    DroneStatus.SEEKING: "🔍",
                    DroneStatus.CONNECTED: "🟢",
                    DroneStatus.MASTER: "👑",
                    DroneStatus.SLAVE: "🔵",
                    DroneStatus.OFFLINE: "⚫",
                    DroneStatus.LOST: "❌"
                }
                
                symbol = status_symbols.get(drone.status, "❓")
                status_display = f"{symbol} {drone.status.value}"
                
                # Position
                x, y, z = drone.position
                position_str = f"({x:5.1f},{y:5.1f},{z:5.1f})"
                
                # Battery with visual indicator
                if drone.battery_level >= 80:
                    battery_str = f"🔋{drone.battery_level:5.1f}%"
                elif drone.battery_level >= 50:
                    battery_str = f"🔋{drone.battery_level:5.1f}%"
                elif drone.battery_level >= 20:
                    battery_str = f"🪫{drone.battery_level:5.1f}%"
                else:
                    battery_str = f"🪫{drone.battery_level:5.1f}%"
                
                # Connection age
                age = time.time() - drone.discovery_time
                if age < 60:
                    age_str = f"{age:4.0f}s"
                elif age < 3600:
                    age_str = f"{age/60:4.0f}m"
                else:
                    age_str = f"{age/3600:4.0f}h"
                
                # Mark self
                self_marker = "→" if drone.is_self else " "
                
                print(f"{self_marker}{drone.drone_id:>5} {status_display:>12} {position_str:>20} {battery_str:>10} {age_str:>8}")
        
        # Network topology
        print("\n📡 Network Topology:")
        print("-" * 30)
        
        online_drones = self.drone_network.get_online_drones()
        
        if not online_drones:
            print("   No drones online")
        else:
            # Group by status
            master_drones = [d for d in online_drones if d.status == DroneStatus.MASTER]
            slave_drones = [d for d in online_drones if d.status == DroneStatus.SLAVE]
            connected_drones = [d for d in online_drones if d.status == DroneStatus.CONNECTED]
            seeking_drones = [d for d in online_drones if d.status == DroneStatus.SEEKING]
            
            if master_drones:
                for master in master_drones:
                    marker = "🔸" if master.is_self else "🔹"
                    print(f"   👑 Master: {marker} Drone {master.drone_id}")
                    
                    if slave_drones:
                        for i, slave in enumerate(slave_drones):
                            marker = "🔸" if slave.is_self else "🔹"
                            connector = "└──" if i == len(slave_drones) - 1 else "├──"
                            print(f"   {connector} Slave: {marker} Drone {slave.drone_id}")
            
            if connected_drones:
                print("   🔗 Connected:")
                for drone in connected_drones:
                    marker = "🔸" if drone.is_self else "🔹"
                    print(f"      • {marker} Drone {drone.drone_id}")
            
            if seeking_drones:
                print("   🔍 Seeking:")
                for drone in seeking_drones:
                    marker = "🔸" if drone.is_self else "🔹"
                    print(f"      • {marker} Drone {drone.drone_id}")
        
        print("="*60 + "\n")

# Compatibility wrapper for existing code
class StateController(EnhancedStateController):
    """Compatibility wrapper to maintain existing interface"""
    
    def __init__(self):
        super().__init__()
        # Map old attributes to new system for compatibility
        self.current_state = self.drone_network.self_drone.status.value
        self.drone_id = self.drone_network.get_self_id()
        self.detected_drones = []
        self.acked_drones = []
    
    def switch_states(self, new_state):
        """Compatibility method for state switching"""
        status_map = {
            "SEEKING": DroneStatus.SEEKING,
            "CONNECTED": DroneStatus.CONNECTED,
            "MASTER": DroneStatus.MASTER,
            "SLAVE": DroneStatus.SLAVE
        }
        
        if new_state in status_map:
            self.drone_network.set_self_status(status_map[new_state])
            self.current_state = new_state
            print(f"Switched to state: {new_state}")
    
    def update_compatibility_attributes(self):
        """Update old-style attributes for compatibility"""
        self.current_state = self.drone_network.self_drone.status.value
        self.drone_id = self.drone_network.get_self_id()
        self.detected_drones = [drone.drone_id for drone in self.drone_network.get_online_drones()]
        self.acked_drones = self.detected_drones.copy()