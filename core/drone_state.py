import random
import time
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum

class DroneStatus(Enum):
    """Enum for drone connection status"""
    OFFLINE = "offline"
    SEEKING = "seeking"
    CONNECTED = "connected"
    MASTER = "master"
    SLAVE = "slave"
    LOST = "lost"

class DroneState:
    """
    Represents the state of a single drone in the network.
    Tracks identity, position, status, and network relationships.
    """
    
    def __init__(self, drone_id: Optional[int] = None):
        self.drone_id = drone_id if drone_id is not None else self._generate_random_id()
        self.status = DroneStatus.SEEKING
        self.last_seen = time.time()
        self.discovery_time = time.time()
        self.position = (random.uniform(-5, 5), random.uniform(-5, 5), 0)  # Random initial position
        self.battery_level = 100.0
        self.is_self = False
        self.ping_count = 0
        self.response_count = 0
        self.signal_strength = 0.0
        self.capabilities = []  # List of drone capabilities
        
    def _generate_random_id(self) -> int:
        """Generate a random 16-bit ID for the drone"""
        return random.randint(1, 65535)
    
    def update_last_seen(self):
        """Update the last seen timestamp"""
        self.last_seen = time.time()
        
    def is_online(self, timeout: float = 30.0) -> bool:
        """Check if drone is considered online based on last seen time"""
        return (time.time() - self.last_seen) < timeout
    
    def get_connection_age(self) -> float:
        """Get how long ago this drone was discovered"""
        return time.time() - self.discovery_time
    
    def update_position(self, x: float, y: float, z: float):
        """Update drone position coordinates"""
        if (x, y, z) == (0.0, 0.0, 0.0):
            print(f"🚨🚨🚨 CRITICAL ERROR: update_position called with (0,0,0) for drone {self.drone_id} 🚨🚨🚨")
            return
        old_position = self.position
        self.position = (x, y, z)
        self.update_last_seen()
        
        # Debug output for position changes - ALWAYS show for self drone
        if self.is_self:
            if self.position == (0.0, 0.0, 0.0) and old_position != (0.0, 0.0, 0.0):
                print(f"🚨🚨🚨 CRITICAL: Self drone {self.drone_id} position RESET to (0,0,0) from {old_position} 🚨🚨🚨")
                import traceback
                traceback.print_stack()
            elif old_position != self.position:
                print(f"📍 Self drone {self.drone_id} position changed: {old_position} -> {self.position}")
    
    def update_battery(self, level: float):
        """Update battery level (0-100)"""
        self.battery_level = max(0.0, min(100.0, level))
        self.update_last_seen()
    
    def increment_ping(self):
        """Increment ping counter"""
        self.ping_count += 1
    
    def increment_response(self):
        """Increment response counter"""
        self.response_count += 1
        
    def get_reliability_score(self) -> float:
        """Calculate reliability score based on ping/response ratio"""
        if self.ping_count == 0:
            return 1.0
        return self.response_count / self.ping_count
    
    def to_dict(self) -> Dict:
        """Convert drone state to dictionary for serialization"""
        return {
            "drone_id": self.drone_id,
            "status": self.status.value,
            "last_seen": self.last_seen,
            "discovery_time": self.discovery_time,
            "position": self.position,
            "battery_level": self.battery_level,
            "ping_count": self.ping_count,
            "response_count": self.response_count,
            "signal_strength": self.signal_strength,
            "capabilities": self.capabilities
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DroneState':
        """Create DroneState from dictionary"""
        drone = cls(data["drone_id"])
        drone.status = DroneStatus(data["status"])
        drone.last_seen = data["last_seen"]
        drone.discovery_time = data["discovery_time"]
        drone.position = tuple(data["position"])
        drone.battery_level = data["battery_level"]
        drone.ping_count = data["ping_count"]
        drone.response_count = data["response_count"]
        drone.signal_strength = data["signal_strength"]
        drone.capabilities = data["capabilities"]
        return drone
    
    def __str__(self) -> str:
        return f"Drone({self.drone_id}, {self.status.value}, {self.position})"

class DroneNetwork:
    """
    Manages the network state of all known drones.
    Handles discovery, conflict resolution, and network topology.
    """
    
    def __init__(self, self_drone_id: Optional[int] = None):
        self.self_drone = DroneState(self_drone_id)
        self.self_drone.is_self = True
        print(f"🚁 Created self drone {self.self_drone.drone_id} with initial position {self.self_drone.position}")
        self.known_drones: Dict[int, DroneState] = {self.self_drone.drone_id: self.self_drone}
        self.master_drone_id: Optional[int] = None
        self.network_established = False
        self.id_conflicts: List[Tuple[int, int]] = []  # List of (conflicting_id, resolved_id) pairs
        
    def get_self_id(self) -> int:
        """Get the ID of this drone"""
        return self.self_drone.drone_id
    
    def set_self_status(self, status: DroneStatus):
        """Update the status of this drone"""
        self.self_drone.status = status
        self.self_drone.update_last_seen()
    
    def add_or_update_drone(self, drone_id: int, status: DroneStatus = DroneStatus.SEEKING, 
                           position: Optional[Tuple[float, float, float]] = None,
                           battery_level = None, signal_strength = None) -> DroneState:
        """Add a new drone or update existing drone information"""
        
        # Debug: Check if we're trying to update the self drone
        if drone_id == self.self_drone.drone_id:
            print(f"🚨🚨🚨 CRITICAL ERROR: add_or_update_drone called for SELF drone {drone_id} with position {position} 🚨🚨🚨")
            import traceback
            traceback.print_stack()
        
        if drone_id in self.known_drones:
            # Update existing drone
            drone = self.known_drones[drone_id]
            drone.status = status
            # Only update position if provided
            if position is not None:
                drone.update_position(*position)
            if battery_level is not None:
                drone.update_battery(battery_level)
            if signal_strength is not None:
                drone.signal_strength = signal_strength
            drone.update_last_seen()
        else:
            # Add new drone
            drone = DroneState(drone_id)
            drone.status = status
            # For new drones, use provided position or keep the random default from DroneState.__init__
            if position is not None:
                drone.update_position(*position)
            if battery_level is not None:
                drone.update_battery(battery_level)
            if signal_strength is not None:
                drone.signal_strength = signal_strength
            self.known_drones[drone_id] = drone
            
        return drone
    
    def remove_drone(self, drone_id: int) -> bool:
        """Remove a drone from the network"""
        if drone_id in self.known_drones and drone_id != self.self_drone.drone_id:
            del self.known_drones[drone_id]
            return True
        return False
    
    def get_drone(self, drone_id: int) -> Optional[DroneState]:
        """Get drone state by ID"""
        return self.known_drones.get(drone_id)
    
    def get_all_drones(self) -> List[DroneState]:
        """Get list of all known drones"""
        return list(self.known_drones.values())
    
    def get_online_drones(self, timeout: float = 30.0) -> List[DroneState]:
        """Get list of all online drones"""
        return [drone for drone in self.known_drones.values() if drone.is_online(timeout)]
    
    def get_drone_count(self) -> int:
        """Get total number of known drones"""
        return len(self.known_drones)
    
    def get_online_drone_count(self, timeout: float = 30.0) -> int:
        """Get number of online drones"""
        return len(self.get_online_drones(timeout))
    
    def cleanup_offline_drones(self, timeout: float = 60.0):
        """Remove drones that have been offline for too long"""
        current_time = time.time()
        offline_drones = [
            drone_id for drone_id, drone in self.known_drones.items()
            if drone_id != self.self_drone.drone_id and 
            (current_time - drone.last_seen) > timeout
        ]
        
        for drone_id in offline_drones:
            self.remove_drone(drone_id)
    
    def detect_id_conflict(self, reported_id: int, reporter_id: int) -> bool:
        """
        Detect if there's an ID conflict between drones.
        Returns True if a conflict is detected.
        """
        if reported_id == self.self_drone.drone_id and reporter_id != self.self_drone.drone_id:
            # Another drone is claiming our ID
            return True
        return False
    
    def resolve_id_conflict(self) -> int:
        """
        Resolve ID conflict by generating a new ID for this drone.
        Returns the new ID.
        """
        old_id = self.self_drone.drone_id
        
        # Generate new ID that doesn't conflict with known drones
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            new_id = random.randint(1, 65535)
            if new_id not in self.known_drones:
                # Update self drone with new ID
                del self.known_drones[old_id]
                self.self_drone.drone_id = new_id
                self.known_drones[new_id] = self.self_drone
                
                # Record the conflict resolution
                self.id_conflicts.append((old_id, new_id))
                
                print(f"ID conflict resolved: {old_id} -> {new_id}")
                return new_id
            attempts += 1
        
        # If we can't find a unique ID after 100 attempts, use timestamp-based ID
        new_id = int(time.time() * 1000) % 65535 + 1
        del self.known_drones[old_id]
        self.self_drone.drone_id = new_id
        self.known_drones[new_id] = self.self_drone
        self.id_conflicts.append((old_id, new_id))
        
        print(f"ID conflict resolved with timestamp-based ID: {old_id} -> {new_id}")
        return new_id
    
    def elect_master(self) -> Optional[int]:
        """
        Elect a master drone based on criteria (lowest ID, highest battery, etc.)
        Returns the master drone ID or None if no suitable master found.
        """
        online_drones = self.get_online_drones()
        
        if not online_drones:
            return None
        
        # Simple election: drone with lowest ID becomes master
        # In a real system, you might consider battery level, capabilities, etc.
        master_candidate = min(online_drones, key=lambda d: d.drone_id)
        self.master_drone_id = master_candidate.drone_id
        
        # Update statuses
        for drone in online_drones:
            if drone.drone_id == self.master_drone_id:
                drone.status = DroneStatus.MASTER
            else:
                drone.status = DroneStatus.SLAVE
                
        return self.master_drone_id
    
    def get_network_topology(self) -> Dict:
        """Get a representation of the network topology"""
        return {
            "self_drone_id": self.self_drone.drone_id,
            "master_drone_id": self.master_drone_id,
            "total_drones": self.get_drone_count(),
            "online_drones": self.get_online_drone_count(),
            "network_established": self.network_established,
            "drones": {drone_id: drone.to_dict() for drone_id, drone in self.known_drones.items()}
        }
    
    def update_network_status(self):
        """Update overall network status based on drone states"""
        online_drones = self.get_online_drones()
        self.network_established = len(online_drones) > 1
        
        # If master is offline, trigger re-election
        if (self.master_drone_id and 
            (self.master_drone_id not in self.known_drones or 
             not self.known_drones[self.master_drone_id].is_online())):
            self.master_drone_id = None
            if self.network_established:
                self.elect_master()
    
    def get_discovery_status(self) -> str:
        """Get a human-readable discovery status"""
        online_count = self.get_online_drone_count()
        total_count = self.get_drone_count()
        
        if online_count == 1:
            return f"Seeking other drones (Found {total_count-1} previously)"
        elif self.network_established:
            master_status = f"Master: {self.master_drone_id}" if self.master_drone_id else "No master"
            return f"Network established: {online_count} drones online. {master_status}"
        else:
            return f"Connecting to network ({online_count} drones found)"
