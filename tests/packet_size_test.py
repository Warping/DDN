import sys
import os
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from networking.drone_packet import DronePacket
from controllers.enhanced_state_controller import EnhancedStateController
from core.drone_state import DroneStatus

def test_network_status_packet_size():
    """Test to ensure network status packets stay under the MTU limit"""
    print("Testing network status packet size...")
    
    # Initialize controller with a random ID
    controller = EnhancedStateController(drone_id=1001, quiet_mode=True)
    
    # Add some drones to the network to simulate a realistic state
    for i in range(1, 10):
        drone_id = 2000 + i
        controller.drone_network.add_or_update_drone(
            drone_id, 
            DroneStatus.SLAVE, 
            (i * 1.5, i * 0.8, 0), 
            battery_level=90 - i, 
            signal_strength=0.8
        )
    
    # Set one drone as master
    controller.drone_network.master_drone_id = 2001
    
    # Get the network state
    network_state = controller.query_network_state()
    
    # Create a packet with the full state (original implementation)
    packet_full = DronePacket()
    packet_full.command(
        None,
        1001,
        -1,
        "master",
        "NETWORK_STATUS",
        {
            "known_drones": network_state,
            "master_id": controller.drone_network.master_drone_id,
            "status_time": datetime.now().timestamp()
        }
    )
    
    # Get the JSON for the full packet
    json_full = packet_full.to_json()
    size_full = len(json_full.encode('utf-8'))
    
    print(f"Original full network state packet size: {size_full} bytes")
    print(f"MTU limit: 500 bytes")
    
    print(f"Full packet exceeds MTU: {'YES' if size_full > 500 else 'NO'}")
    print("-" * 50)
    
    # Now test the new positions-included format
    packet_new = DronePacket()
    result = packet_new.network_status(
        None,
        1001,
        "master",
        network_state,
        controller.drone_network.master_drone_id
    )
    
    # Get the JSON for the new implementation (should use positions-only format if needed)
    json_new = packet_new.to_json()
    size_new = len(json_new.encode('utf-8'))
    
    print(f"New format packet size: {size_new} bytes")
    print(f"New format exceeds MTU: {'YES' if size_new > 500 else 'NO'}")
    
    if size_new <= 500:
        print("✅ SUCCESS: The packet size is now under the MTU limit!")
    else:
        print("❌ FAILED: Packet is still too large, further optimization needed.")
    
    print("-" * 50)
    print("New format packet structure preview:")
    packet_structure = json.loads(json_new)
    
    # Check if we have drone data with positions (in any format)
    has_positions = False
    if "params" in packet_structure:
        params = packet_structure["params"]
        
        # Check for optimized format
        if "opt" in params and params.get("opt") and "d" in params:
            drones = params["d"]
            num_drones = len(drones)
            print(f"Number of drones in OPTIMIZED packet: {num_drones}")
            if num_drones > 0:
                print("Sample drone data (optimized format):")
                sample_drone = drones[0]
                print(json.dumps(sample_drone, indent=2))
                
                if "p" in sample_drone:  # Optimized position key
                    has_positions = True
                    print("✅ SUCCESS: Position data is included in the optimized packet!")
                else:
                    print("❌ FAILED: Position data is missing from the optimized packet.")
        
        # Check for original drone format
        elif "drones" in params:
            num_drones = len(params["drones"])
            print(f"Number of drones in packet: {num_drones}")
            if num_drones > 0:
                print("Sample drone data:")
                sample_drone = params["drones"][0]
                print(json.dumps(sample_drone, indent=2))
                
                if "pos" in sample_drone:
                    has_positions = True
                    print("✅ SUCCESS: Position data is included in the packet!")
                else:
                    print("❌ FAILED: Position data is missing from the packet.")
        
        # Check for basic format
        elif "known_drones" in params:
            print("Using basic format with just drone IDs - positions NOT included")
            print(json.dumps(params, indent=2))
            print("❌ FAILED: Position data is missing from the packet.")
        
        # Show the entire params structure for debugging
        else:
            print("Packet structure:")
            print(json.dumps(params, indent=2))
    
    if not has_positions:
        print("❌ FAILED: No drone data with positions found in the packet.")

if __name__ == "__main__":
    test_network_status_packet_size()