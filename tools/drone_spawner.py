#!/usr/bin/env python3
"""
Drone Network Spawner

This script allows you to spawn multiple drones, manage them, and remove them.
Each drone runs in its own process to simulate a real distributed network.
"""

import subprocess
import time
import signal
import sys
import os
from typing import Dict, List, Optional

class DroneSpawner:
    """
    Manages spawning and removing drone processes
    """
    
    def __init__(self):
        self.active_drones: Dict[int, subprocess.Popen] = {}
        self.next_auto_id = 1001
        
    def spawn_drone(self, drone_id: Optional[int] = None, use_visualizer: bool = False) -> int:
        """
        Spawn a new drone process
        
        Args:
            drone_id: Specific ID for the drone (None for auto-generated)
            use_visualizer: Whether to spawn with visualizer dashboard
            
        Returns:
            The drone ID that was spawned
        """
        if drone_id is None:
            # Auto-generate ID
            while self.next_auto_id in self.active_drones:
                self.next_auto_id += 1
            drone_id = self.next_auto_id
            self.next_auto_id += 1
        
        if drone_id in self.active_drones:
            print(f"❌ Drone {drone_id} is already running!")
            return drone_id
        
        # Choose which script to run
        if use_visualizer:
            # For visualizer, just run the passive visualizer (no drone spawning)
            cmd = ["python", "drone_visualizer.py", "--mode", "realtime"]
        else:
            cmd = ["python", "applications/run_drone.py", str(drone_id)]
        
        try:
            # Spawn the drone process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # Create new process group for clean termination
            )
            
            self.active_drones[drone_id] = process
            mode = "with visualizer" if use_visualizer else "headless"
            print(f"✅ Spawned drone {drone_id} {mode} (PID: {process.pid})")
            return drone_id
            
        except Exception as e:
            print(f"❌ Failed to spawn drone {drone_id}: {e}")
            return drone_id
    
    def remove_drone(self, drone_id: int) -> bool:
        """
        Remove (terminate) a drone process
        
        Args:
            drone_id: ID of the drone to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        if drone_id not in self.active_drones:
            print(f"❌ Drone {drone_id} is not running!")
            return False
        
        process = self.active_drones[drone_id]
        
        try:
            # Terminate the process gracefully
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            # Wait for termination with timeout
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
            
            del self.active_drones[drone_id]
            print(f"✅ Removed drone {drone_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to remove drone {drone_id}: {e}")
            return False
    
    def list_drones(self):
        """List all active drones"""
        if not self.active_drones:
            print("📭 No active drones")
            return
        
        print(f"🚁 Active Drones ({len(self.active_drones)}):")
        for drone_id, process in self.active_drones.items():
            status = "Running" if process.poll() is None else "Stopped"
            print(f"   Drone {drone_id}: {status} (PID: {process.pid})")
    
    def remove_all_drones(self):
        """Remove all active drones"""
        drone_ids = list(self.active_drones.keys())
        for drone_id in drone_ids:
            self.remove_drone(drone_id)
        print(f"✅ Removed all {len(drone_ids)} drones")
    
    def spawn_multiple(self, count: int, start_id: Optional[int] = None, use_visualizer: bool = False):
        """
        Spawn multiple drones at once
        
        Args:
            count: Number of drones to spawn
            start_id: Starting ID (None for auto-generated)
            use_visualizer: Whether to spawn with visualizers
        """
        print(f"🚁 Spawning {count} drones...")
        
        spawned_ids = []
        for i in range(count):
            if start_id is not None:
                drone_id = start_id + i
            else:
                drone_id = None
            
            spawned_id = self.spawn_drone(drone_id, use_visualizer)
            spawned_ids.append(spawned_id)
            time.sleep(0.5)  # Small delay between spawns
        
        print(f"✅ Spawned drones: {spawned_ids}")
        return spawned_ids
    
    def cleanup(self):
        """Cleanup all processes on exit"""
        self.remove_all_drones()

def interactive_mode():
    """Interactive mode for managing drones"""
    spawner = DroneSpawner()
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        spawner.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚁 DRONE NETWORK SPAWNER")
    print("=" * 40)
    print("Commands:")
    print("  spawn [id] [viz]     - Spawn drone (optional ID, viz for visualizer)")
    print("  remove <id>          - Remove drone by ID")
    print("  list                 - List active drones")
    print("  spawn_multiple <n>   - Spawn N drones")
    print("  remove_all           - Remove all drones")
    print("  quit                 - Exit")
    print("=" * 40)
    
    try:
        while True:
            try:
                cmd = input("\n🚁 > ").strip().split()
                if not cmd:
                    continue
                if cmd[0] == "spawn":
                    drone_id = None
                    use_viz = False
                    
                    if len(cmd) > 1 and cmd[1].isdigit():
                        drone_id = int(cmd[1])
                    if len(cmd) > 2 and cmd[2] == "viz":
                        use_viz = True
                    elif len(cmd) > 1 and cmd[1] == "viz":
                        use_viz = True
                    
                    spawner.spawn_drone(drone_id, use_viz)
                
                elif cmd[0] == "remove":
                    if len(cmd) < 2:
                        print("❌ Usage: remove <drone_id>")
                        continue
                    try:
                        drone_id = int(cmd[1])
                        spawner.remove_drone(drone_id)
                    except ValueError:
                        print("❌ Invalid drone ID")
                
                elif cmd[0] == "list":
                    spawner.list_drones()
                
                elif cmd[0] == "spawn_multiple":
                    if len(cmd) < 2:
                        print("❌ Usage: spawn_multiple <count>")
                        continue
                    try:
                        count = int(cmd[1])
                        spawner.spawn_multiple(count)
                    except ValueError:
                        print("❌ Invalid count")
                
                elif cmd[0] == "remove_all":
                    spawner.remove_all_drones()
                
                elif cmd[0] in ["quit", "exit", "q"]:
                    break
                
                else:
                    print("❌ Unknown command")
            except EOFError:
                # Handle EOF (Ctrl+D or piped input)
                print("\n🛑 Exiting...")
                break
                
                
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        spawner.cleanup()

def main():
    """Main function with command line interface"""
    # Check for help first
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        print("Usage:")
        print("  python drone_spawner.py                    # Interactive mode")
        print("  python drone_spawner.py spawn [id] [viz]   # Spawn single drone")
        print("  python drone_spawner.py spawn_multiple 3  # Spawn 3 drones")
        return
    
    if len(sys.argv) == 1:
        # No arguments - start interactive mode
        interactive_mode()
        return
    
    spawner = DroneSpawner()
    
    def cleanup_handler(sig, frame):
        spawner.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    
    # Parse command line arguments
    if sys.argv[1] == "spawn":
        drone_id = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        use_viz = "viz" in sys.argv
        spawner.spawn_drone(drone_id, use_viz)
        
        # Keep script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    elif sys.argv[1] == "spawn_multiple":
        count = int(sys.argv[2])
        start_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
        use_viz = "viz" in sys.argv
        spawner.spawn_multiple(count, start_id, use_viz)
        
        # Keep script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    else:
        print("Usage:")
        print("  python drone_spawner.py                    # Interactive mode")
        print("  python drone_spawner.py spawn [id] [viz]   # Spawn single drone")
        print("  python drone_spawner.py spawn_multiple 3  # Spawn 3 drones")

if __name__ == "__main__":
    main()