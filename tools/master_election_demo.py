#!/usr/bin/env python3
"""
Master Election Test Script

This script demonstrates the master election and re-election functionality.
"""

import time
import subprocess
import sys
import signal

class MasterElectionDemo:
    def __init__(self):
        self.processes = {}
        
    def start_drone(self, drone_id):
        """Start a drone process"""
        try:
            process = subprocess.Popen([
                sys.executable, "run_drone.py", str(drone_id)
            ])
            self.processes[drone_id] = process
            print(f"✅ Started drone {drone_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to start drone {drone_id}: {e}")
            return False
    
    def stop_drone(self, drone_id):
        """Stop a specific drone"""
        if drone_id in self.processes:
            try:
                self.processes[drone_id].terminate()
                self.processes[drone_id].wait(timeout=3)
                del self.processes[drone_id]
                print(f"🛑 Stopped drone {drone_id}")
                return True
            except subprocess.TimeoutExpired:
                self.processes[drone_id].kill()
                del self.processes[drone_id]
                print(f"⚠️  Force killed drone {drone_id}")
                return True
            except Exception as e:
                print(f"❌ Error stopping drone {drone_id}: {e}")
                return False
        return False
    
    def cleanup_all(self):
        """Stop all drone processes"""
        drone_ids = list(self.processes.keys())
        for drone_id in drone_ids:
            self.stop_drone(drone_id)
        print(f"🧹 Cleaned up {len(drone_ids)} drones")
    
    def run_demo(self):
        """Run the master election demonstration"""
        print("🚁 MASTER ELECTION DEMONSTRATION")
        print("=" * 50)
        
        try:
            # Phase 1: Start initial network
            print("\n📡 Phase 1: Starting initial network...")
            self.start_drone(1001)  # Lowest ID - should become master
            time.sleep(2)
            self.start_drone(1003)  # Higher ID - should become slave
            time.sleep(2)
            self.start_drone(1002)  # Middle ID - should become slave
            
            print("\n⏳ Waiting 20 seconds for network formation and master election...")
            time.sleep(20)
            
            # Phase 2: Add more drones
            print("\n📡 Phase 2: Adding more drones to existing network...")
            self.start_drone(999)   # Even lower ID - should trigger re-election
            time.sleep(2)
            self.start_drone(1005)  # Higher ID - should join as slave
            
            print("\n⏳ Waiting 15 seconds for network updates...")
            time.sleep(15)
            
            # Phase 3: Remove current master to trigger re-election
            print("\n💥 Phase 3: Simulating master failure...")
            print("Stopping current master (drone with lowest ID)...")
            
            # Find and stop the lowest ID drone (current master)
            if 999 in self.processes:
                self.stop_drone(999)
                print("Stopped drone 999 (likely master)")
            elif 1001 in self.processes:
                self.stop_drone(1001)
                print("Stopped drone 1001 (likely master)")
            
            print("\n⏳ Waiting 30 seconds for master re-election...")
            time.sleep(30)
            
            # Phase 4: Add new drone to see if it joins properly
            print("\n📡 Phase 4: Adding new drone after re-election...")
            self.start_drone(998)   # Should join as slave to new master
            
            print("\n⏳ Final observation period (20 seconds)...")
            time.sleep(20)
            
            print("\n✅ Demo complete!")
            print("\n💡 During this demo, you should have observed:")
            print("   1. Initial master election (lowest ID)")
            print("   2. Possible re-election when drone 999 joined")
            print("   3. Re-election when master was stopped")
            print("   4. New drone joining established network")
            print("\n💡 You can run the passive visualizer in another terminal:")
            print("   python drone_visualizer.py")
            
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")
        finally:
            print("\n🧹 Cleaning up...")
            self.cleanup_all()

def main():
    demo = MasterElectionDemo()
    
    # Set up signal handler for clean exit
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down demo...")
        demo.cleanup_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    demo.run_demo()

if __name__ == "__main__":
    main()