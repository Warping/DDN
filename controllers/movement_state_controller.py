import math

class MovementStateController():
    def __init__(self, network_state, old_network_state):
        self.network_state = network_state
        self.old_network_state = old_network_state
        # self.positions = {}  # Store positions of drones
        # self.velocities = {}  # Store velocities of drones
    
    def get_positions(self, state):
        """Extract positions from the network state"""
        print("Getting positions from state...")
        positions = {}
        for drone in state.get('all_drones', []):
            drone_id = drone['drone_id']
            position = drone.get('position', None)
            if drone.get('is_online', False) and position:
                positions[drone_id] = position
        return positions
    
    def get_velocities(self, current_state, old_state):
        """Calculate velocities based on position changes over time"""
        current_positions = self.get_positions(current_state)
        old_positions = self.get_positions(old_state)
        
        delta_t = current_state['timestamp'] - old_state['timestamp']
        velocities = {}
        for drone_id, current_pos in current_positions.items():
            old_pos = old_positions.get(drone_id, None)
            if current_pos and old_pos and delta_t > 0:
                velocity = (
                    (current_pos[0] - old_pos[0]) / delta_t,
                    (current_pos[1] - old_pos[1]) / delta_t,
                    (current_pos[2] - old_pos[2]) / delta_t
                )
                velocities[drone_id] = velocity
            else:
                velocities[drone_id] = (0.0, 0.0, 0.0)  # Default to zero if no movement or no previous data
        return velocities
    
    
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
        
        # Sort by drone_id as integers in ascending order to process lowest IDs first
        for drone_id, pos in sorted(positions.items(), key=lambda item: int(item[0])):
            if available_points:
                closest_point = self.find_closest_point(pos, available_points)
                pairing[drone_id] = closest_point
                available_points.remove(closest_point)
                if pairing[drone_id] == positions[drone_id]:
                    pairing[drone_id] = None  # No movement needed if already at the point
            else:
                pairing[drone_id] = None  # No available point
        
        return pairing
    
    def update_slave_positions(self):
        """Update slave drone positions based on master position and velocity"""
        print("Updating slave positions...")
        all_drone_pos = self.get_positions(self.network_state)
        if not all_drone_pos:
            print("No drone positions available in the current network state.")
            return {}
        print(f"All drone positions: {all_drone_pos}")
        master_pos = all_drone_pos.pop(self.network_state.get('network_stats', {}).get('current_master_id', None), None)
        print(f"Master position: {master_pos}")
        if master_pos is None:
            print("No master position found, cannot update slave positions.")
            return {}
        print(f"Remaining drone positions (slaves): {all_drone_pos}")
        drone_count = len(all_drone_pos)
        if drone_count == 0:
            print("No slave drones to update.")
            return {}
        circle_points = self.get_points_along_circle(master_pos, radius=2.0, num_points=drone_count)
        print(f"Drone count (excluding master): {drone_count}")
        print(f"Calculated circle points: {circle_points}")
        
        pairings = self.pair_drones_to_positions(all_drone_pos, circle_points)
        print(f"Pairings of drones to positions: {pairings}")
        return pairings
        # movement_vectors = {}
        # for drone_id, target_pos in pairings.items():
        #     current_pos = all_drone_pos.get(drone_id, None)
        #     if current_pos and target_pos and current_pos != target_pos:
        #         movement_vector = self.calc_vector(current_pos, target_pos)
        #         print(f"Drone {drone_id} moving from {current_pos} to {target_pos} with vector {movement_vector}")
        #         unit_movement_vector = tuple(v / math.dist(current_pos, target_pos) if math.dist(current_pos, target_pos) > 1 else v for v in movement_vector)
        #         print(f"  Unit movement vector: {unit_movement_vector}")
        #         movement_vectors[drone_id] = unit_movement_vector
        #     else:
        #         movement_vectors[drone_id] = (0.0, 0.0, 0.0)  # No movement needed or no current position
        # return movement_vectors