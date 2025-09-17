#!/usr/bin/env python3
"""
Simple drone runner for testing
"""

import sys
import time
from enhanced_state_controller import EnhancedStateController
from drone_state import DroneStatus

def main():
    drone_id = None
    quiet_mode = True  # Default to quiet for testing
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            drone_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid drone ID: {sys.argv[1]}")
            sys.exit(1)
    
    # Check for quiet flag
    if len(sys.argv) > 2 and sys.argv[2] == "--verbose":
        quiet_mode = False
    
    print(f"🚁 Starting drone {drone_id if drone_id else 'with random ID'}...")
    
    try:
        # Create enhanced state controller
        controller = EnhancedStateController(drone_id, quiet_mode=quiet_mode)
        
        print(f"✅ Drone {controller.drone_network.get_self_id()} is running")
        print("Press Ctrl+C to stop")
        
        # Main control loop
        while True:
            current_time = time.time()
            
            # Process incoming packets
            controller.process_incoming_packets()
            
            # Discovery logic
            if (controller.drone_network.self_drone.status == DroneStatus.SEEKING and
                current_time - controller.last_discovery_time > controller.discovery_interval and
                controller.discovery_attempts < controller.max_discovery_attempts):
                
                controller.send_discovery_announcement()
                controller.last_discovery_time = current_time
            
            # Heartbeat logic
            if (controller.drone_network.self_drone.status in [DroneStatus.CONNECTED, 
                                                               DroneStatus.MASTER, 
                                                               DroneStatus.SLAVE] and
                current_time - controller.last_heartbeat_time > controller.heartbeat_interval):
                
                controller.send_heartbeat()
                controller.last_heartbeat_time = current_time
            
            # Network status sharing (especially important for masters)
            if (controller.drone_network.self_drone.status == DroneStatus.MASTER and
                current_time - controller.last_network_sync_time > controller.network_sync_interval):
                
                controller.share_network_status()
                controller.last_network_sync_time = current_time
            
            # Update state (includes master election logic)
            controller.update_state_based_on_network()
            
            time.sleep(0.1)  # Small delay to prevent high CPU usage
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping drone {controller.drone_network.get_self_id()}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()