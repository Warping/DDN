import os
import sys
import threading

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from controllers.enhanced_state_controller import EnhancedStateController

class DroneSpawner:
    
    def __init__(self):
        self.controllers = {}
    
    def spawn_drone(self, drone_id):
        """Spawn a new drone controller thread"""
        if drone_id in self.controllers:
            print(f"❌ Drone {drone_id} already exists")
            return False
        
        try:
            controller = EnhancedStateController(drone_id)
            thread = threading.Thread(target=controller.control_loop, daemon=True)
            thread.start()
            self.controllers[drone_id] = (controller, thread)
            print(f"✅ Spawned drone {drone_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to spawn drone {drone_id}: {e}")
            return False
        
    def stop_drone(self, drone_id):
        """Stop a specific drone controller"""
        if drone_id in self.controllers:
            try:
                controller, thread = self.controllers[drone_id]
                controller.stop()
                thread.join(timeout=3)
                del self.controllers[drone_id]
                print(f"🛑 Stopped drone {drone_id}")
                return True
            except Exception as e:
                print(f"❌ Error stopping drone {drone_id}: {e}")
                return False
        return False
    
    def cleanup_all(self):
        """Stop all drone controllers"""
        drone_ids = list(self.controllers.keys())
        for drone_id in drone_ids:
            self.stop_drone(drone_id)
        print(f"🧹 Cleaned up {len(drone_ids)} drones")
        
    def interactive_shell(self):
        """Simple interactive shell to manage drones"""
        print("🚁 Drone Spawner Interactive Shell")
        print("Commands: spawn <id>, stop <id>, list, exit")
        
        while True:
            try:
                command = input(">> ").strip().lower()
                if command.startswith("spawn "):
                    _, drone_id = command.split()
                    self.spawn_drone(int(drone_id))
                elif command.startswith("stop "):
                    _, drone_id = command.split()
                    self.stop_drone(int(drone_id))
                elif command == "list":
                    if self.controllers:
                        print("Active drones:", ", ".join(map(str, self.controllers.keys())))
                    else:
                        print("No active drones")
                elif command == "exit":
                    break
                else:
                    print("Unknown command")
            except Exception as e:
                print(f"Error: {e}")
        
        self.cleanup_all()
        
if __name__ == "__main__":
    try:
        spawner = DroneSpawner()
        spawner.interactive_shell()
    except KeyboardInterrupt:
        print("\nExiting...")
        spawner.cleanup_all()
        sys.exit(0)
            
    