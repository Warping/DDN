import math

class MovementStateController():
    def __init__(self, network_state, old_network_state):
        self.network_state = network_state
        self.old_network_state = old_network_state
        self.positions = {}  # Store positions of drones
        self.velocities = {}  # Store velocities of drones
    
    def get_positions(self, state):
        """Extract positions from the network state"""
        for drone in state.get('all_drones', []):
            drone_id = drone['drone_id']
            position = drone.get('position', None)
            self.positions[drone_id] = position
        return self.positions
    
    def get_velocities(self, current_state, old_state):
        """Calculate velocities based on position changes over time"""
        current_positions = self.get_positions(current_state)
        old_positions = self.get_positions(old_state)
        
        delta_t = current_state['timestamp'] - old_state['timestamp']
        
        for drone_id, current_pos in current_positions.items():
            old_pos = old_positions.get(drone_id, None)
            if current_pos and old_pos and delta_t > 0:
                velocity = (
                    (current_pos[0] - old_pos[0]) / delta_t,
                    (current_pos[1] - old_pos[1]) / delta_t,
                    (current_pos[2] - old_pos[2]) / delta_t
                )
                self.velocities[drone_id] = velocity
            else:
                self.velocities[drone_id] = (0.0, 0.0, 0.0)  # Default to zero if no movement or no previous data
        return self.velocities
    
    def get_master_position(self):
        """Get the position of the master drone"""
        # print("Getting master position...")
        master_id = self.network_state.get('network_stats', {}).get('current_master_id', None)
        # print(f"Master ID: {master_id}")
        if master_id:
            return self.positions.get(master_id, None)
        return None
    
    def get_master_velocity(self):
        """Get the velocity of the master drone"""
        master_id = self.network_state.get('network_stats', {}).get('current_master_id', None)
        if master_id:
            return self.velocities.get(master_id, None)
        return None
    
    def get_points_along_circle(self, center, radius, num_points=8):
        """Calculate points evenly distributed along a circle in the XY plane"""
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            z = center[2]  # Keep the same altitude
            points.append((x, y, z))
        return points
    
    def calc_vector(self, from_pos, to_pos):
        """Calculate vector from one position to another"""
        return (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1], to_pos[2] - from_pos[2])
    
    def find_closest_point(self, position, points):
        """Find the closest point from a list of points to a given position"""
        closest_point = None
        min_distance = float('inf')
        for point in points:
            distance = math.dist(position, point)
            if distance < min_distance:
                min_distance = distance
                closest_point = point
        return closest_point
    
    def pair_drones_to_positions(self, positions, points):
        """Pair drones to the closest available points"""
        pairing = {}
        available_points = points.copy()
        
        for drone_id, pos in positions.items():
            if available_points:
                closest_point = self.find_closest_point(pos, available_points)
                pairing[drone_id] = closest_point
                available_points.remove(closest_point)
            else:
                pairing[drone_id] = None  # No available point
        
        return pairing
    
    def update_slave_positions(self):
        """Update slave drone positions based on master position and velocity"""
        print("Updating slave positions...")
        master_pos = self.get_master_position()
        slave_drone_pos = self.get_positions(self.network_state).copy()
        drone_count = len(self.positions) - 1  # Exclude master
        circle_points = self.get_points_along_circle(master_pos, radius=5.0, num_points=drone_count)
        print(f"Current positions: {self.positions}")
        print(f"Drone count (excluding master): {drone_count}")
        print(f"Master position: {master_pos}")
        print(f"Slave drone positions before update: {slave_drone_pos}")
        print(f"Calculated circle points: {circle_points}")
        if master_pos in slave_drone_pos.values():
            master_id = self.network_state.get('network_stats', {}).get('current_master_id', None)
            if master_id is not None:
                del slave_drone_pos[master_id]
            else:
                print("Warning: Master ID not found in network state")
                return None
        pairing = self.pair_drones_to_positions(slave_drone_pos, circle_points)
        new_positions = {}
        for pair in pairing.items():
            drone_id, target_pos = pair
            if target_pos:
                print(f"Drone {drone_id} moving to position {target_pos}")
            else:
                print(f"Drone {drone_id} has no assigned position")
                return None
            # Calc movement vector
            current_pos = self.positions.get(drone_id, None)
            if current_pos and target_pos:
                movement_vector = self.calc_vector(current_pos, target_pos)
                print(f"  Movement vector: {movement_vector}")
            else:
                print(f"  No movement vector calculated for Drone {drone_id}")
                return None
            # Scale movement vector to desired speed (e.g., 1 unit per second)
            movement_vector = tuple(v * 0.1 for v in movement_vector)  # Scale down for demonstration
            new_positions[drone_id] = movement_vector
        return new_positions