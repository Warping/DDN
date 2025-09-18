#!/usr/bin/env python3
"""
Programmatic Drone Management Example

Shows how to dynamically add/remove drones from your network programmatically.
This simulates drones joining and leaving the network during operation.
"""

import time
import random
import threading
from typing import Optional
from controllers.enhanced_state_controller import EnhancedStateController
from visualization.drone_visualizer import DroneNetworkVisualizer, PassiveNetworkMonitor
from core.drone_state import DroneStatus

class NetworkManager:
    """
    Manages a network of drones programmatically
    """
    
    def __init__(self):
        self.controllers = {}
        self.visualizer = None
        self.running = True
        
    def add_drone(self, drone_id: Optional[int] = None, with_visualizer: bool = False):
        """
        Add a new drone to the network
        
        Args:
            drone_id: Specific ID for the drone (None for random)
            with_visualizer: Whether to attach visualizer to this drone
        """
        if drone_id is None:
            # Generate random ID that doesn't conflict
            while True:
                drone_id = random.randint(1000, 9999)
                if drone_id not in self.controllers:
                    break
        
        if drone_id in self.controllers:
            print(f"❌ Drone {drone_id} already exists in network!")
            return None
        
        # Create new drone controller
        controller = EnhancedStateController(drone_id, quiet_mode=True)
        self.controllers[drone_id] = controller
        
        # Add visualizer if requested and none exists
        if with_visualizer and self.visualizer is None:
            # Create a passive monitor for visualization
            passive_monitor = PassiveNetworkMonitor()
            self.visualizer = DroneNetworkVisualizer(passive_monitor)
        
        print(f"✅ Added drone {drone_id} to network")
        
        # Start drone in background thread
        def run_drone():
            try:
                while self.running and drone_id in self.controllers:
                    current_time = time.time()
                    
                    # Process packets
                    controller.process_incoming_packets()
                    
                    # Discovery logic
                    if (controller.drone_network.self_drone.status == DroneStatus.SEEKING and
                        current_time - controller.last_discovery_time > controller.discovery_interval and
                        controller.discovery_attempts < controller.max_discovery_attempts):
                        
                        controller.send_discovery_announcement()
                        controller.last_discovery_time = current_time
                    
                    # Heartbeat logic
                    if (controller.drone_network.self_drone.status in [DroneStatus.CONNECTED, DroneStatus.MASTER, DroneStatus.SLAVE] and
                        current_time - controller.last_heartbeat_time > controller.heartbeat_interval):
                        
                        controller.send_heartbeat()
                        controller.last_heartbeat_time = current_time
                    
                    # Update state
                    controller.update_state_based_on_network()
                    
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ Drone {drone_id} error: {e}")
        
        # Start drone thread
        thread = threading.Thread(target=run_drone, daemon=True)
        thread.start()
        
        return controller
    
    def remove_drone(self, drone_id: int):
        """
        Remove a drone from the network
        
        Args:
            drone_id: ID of the drone to remove
        """
        if drone_id not in self.controllers:
            print(f"❌ Drone {drone_id} not found in network!")
            return False
        
        # Remove from controllers (this will stop the thread)
        del self.controllers[drone_id]
        print(f"✅ Removed drone {drone_id} from network")
        return True
    
    def get_network_status(self):
        """Get status of all drones in the network"""
        if not self.controllers:
            return "📭 No drones in network"
        
        status_lines = [f"🚁 Network Status ({len(self.controllers)} drones):"]
        
        for drone_id, controller in self.controllers.items():
            drone = controller.drone_network.self_drone
            online_count = controller.drone_network.get_online_drone_count()
            status_lines.append(f"   Drone {drone_id}: {drone.status.value} | Sees {online_count} drones")
        
        return "\n".join(status_lines)
    
    def start_visualizer(self):
        """Start real-time visualization using passive monitor"""
        from visualization.drone_visualizer import PassiveNetworkMonitor, DroneNetworkVisualizer
        
        if self.visualizer is None:
            # Create a passive monitor for visualization
            monitor = PassiveNetworkMonitor()
            self.visualizer = DroneNetworkVisualizer(monitor)
        
        if self.visualizer:
            print("🎯 Starting network visualizer...")
            self.visualizer.real_time_display()
    
    def shutdown(self):
        """Shutdown all drones"""
        self.running = False
        drone_ids = list(self.controllers.keys())
        for drone_id in drone_ids:
            self.remove_drone(drone_id)
        print(f"✅ Shutdown complete - removed {len(drone_ids)} drones")

def demo_dynamic_network():
    """Demo showing dynamic drone addition/removal"""
    print("🚁 DYNAMIC DRONE NETWORK DEMO")
    print("=" * 40)
    
    manager = NetworkManager()
    
    try:
        # Start with 2 drones
        print("📡 Starting initial network...")
        manager.add_drone(1001)
        manager.add_drone(1002, with_visualizer=True)
        time.sleep(3)
        
        print(manager.get_network_status())
        time.sleep(5)
        
        # Add more drones dynamically
        print("\n🚁 Adding more drones...")
        manager.add_drone(1003)
        time.sleep(2)
        manager.add_drone(1004)
        time.sleep(3)
        
        print(manager.get_network_status())
        time.sleep(5)
        
        # Remove some drones
        print("\n❌ Removing some drones...")
        manager.remove_drone(1002)
        time.sleep(2)
        manager.remove_drone(1004)
        time.sleep(3)
        
        print(manager.get_network_status())
        time.sleep(5)
        
        # Add drones with random IDs
        print("\n🎲 Adding drones with random IDs...")
        manager.add_drone()  # Random ID
        manager.add_drone()  # Random ID
        time.sleep(3)
        
        print(manager.get_network_status())
        
        print("\n✅ Demo complete - press Ctrl+C to exit")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
    finally:
        manager.shutdown()

def interactive_network_manager():
    """Interactive network management"""
    manager = NetworkManager()
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        manager.shutdown()
        sys.exit(0)
    
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚁 INTERACTIVE NETWORK MANAGER")
    print("=" * 40)
    print("Commands:")
    print("  add [id]         - Add drone (optional specific ID)")
    print("  remove <id>      - Remove drone by ID")
    print("  status           - Show network status")
    print("  visualize        - Start real-time visualizer")
    print("  quit             - Exit")
    print("=" * 40)
    
    try:
        while True:
            try:
                cmd = input("\n🚁 > ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == "add":
                    drone_id = int(cmd[1]) if len(cmd) > 1 and cmd[1].isdigit() else None
                    manager.add_drone(drone_id)
                
                elif cmd[0] == "remove":
                    if len(cmd) < 2:
                        print("❌ Usage: remove <drone_id>")
                        continue
                    try:
                        drone_id = int(cmd[1])
                        manager.remove_drone(drone_id)
                    except ValueError:
                        print("❌ Invalid drone ID")
                
                elif cmd[0] == "status":
                    print(manager.get_network_status())
                
                elif cmd[0] == "visualize":
                    manager.start_visualizer()
                
                elif cmd[0] in ["quit", "exit", "q"]:
                    break
                
                else:
                    print("❌ Unknown command")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        manager.shutdown()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_dynamic_network()
    else:
        interactive_network_manager()