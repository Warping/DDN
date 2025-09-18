#!/usr/bin/env python3
"""
Master Death Detection Test

This script tests that slaves properly detect when a master dies and re-elect a new one.
"""

import subprocess
import time
import sys
import signal
import os

class MasterDeathTest:
    def __init__(self):
        self.processes = {}
        
    def start_drone(self, drone_id):
        """Start a drone process"""
        try:
            process = subprocess.Popen([
                sys.executable, "run_drone.py", str(drone_id)
            ])
            self.processes[drone_id] = process
            print(f"✅ Started drone {drone_id} (PID: {process.pid})")
            return True
        except Exception as e:
            print(f"❌ Failed to start drone {drone_id}: {e}")
            return False
    
    def kill_drone(self, drone_id):
        """Kill a specific drone process"""
        if drone_id in self.processes:
            try:
                process = self.processes[drone_id]
                process.terminate()
                process.wait(timeout=3)
                del self.processes[drone_id]
                print(f"💀 Killed drone {drone_id}")
                return True
            except subprocess.TimeoutExpired:
                process.kill()
                del self.processes[drone_id]
                print(f"💀 Force killed drone {drone_id}")
                return True
            except Exception as e:
                print(f"❌ Error killing drone {drone_id}: {e}")
                return False
        return False
    
    def cleanup_all(self):
        """Kill all drone processes"""
        drone_ids = list(self.processes.keys())
        for drone_id in drone_ids:
            self.kill_drone(drone_id)
    
    def run_test(self):
        """Run the master death detection test"""
        print("💀 MASTER DEATH DETECTION TEST")
        print("=" * 50)
        
        try:
            # Start network with 5 drones
            print("\n📡 Phase 1: Starting network with 5 drones...")
            drone_ids = [1001, 1002, 1003, 1004, 1005]
            
            for drone_id in drone_ids:
                self.start_drone(drone_id)
                time.sleep(1)  # Stagger startup
            
            print(f"\n⏳ Waiting 20 seconds for network formation...")
            print("   Expected: Drone 1001 should become master (lowest ID)")
            time.sleep(20)
            
            # Kill the master (1001)
            print(f"\n💀 Phase 2: Killing master drone 1001...")
            self.kill_drone(1001)
            
            print(f"\n⏳ Waiting 30 seconds for master death detection and re-election...")
            print("   Expected: Remaining drones should detect 1001 is dead")
            print("   Expected: Drone 1002 should become new master (next lowest ID)")
            print("   Watch for messages like:")
            print("   - 'Master drone 1001 is offline'") 
            print("   - 'Starting master election'")
            print("   - 'Elected as MASTER' or 'elected as MASTER'")
            time.sleep(30)
            
            # Add another drone to test if it joins the new master
            print(f"\n📡 Phase 3: Adding new drone 1006 to test master recognition...")
            self.start_drone(1006)
            
            print(f"\n⏳ Waiting 15 seconds for new drone integration...")
            print("   Expected: Drone 1006 should recognize 1002 as master")
            time.sleep(15)
            
            # Kill the new master to test re-election again
            print(f"\n💀 Phase 4: Killing new master drone 1002...")
            self.kill_drone(1002)
            
            print(f"\n⏳ Final 20 seconds - second re-election test...")
            print("   Expected: Drone 1003 should become the new master")
            time.sleep(20)
            
            print("\n✅ Test complete!")
            print("\n💡 What you should have observed:")
            print("   1. Initial master election: 1001 becomes master")
            print("   2. Master death detection: slaves detect 1001 is offline")
            print("   3. Re-election: 1002 becomes new master") 
            print("   4. New drone integration: 1006 recognizes 1002 as master")
            print("   5. Second master death: 1002 dies")
            print("   6. Second re-election: 1003 becomes final master")
            
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
        finally:
            print("\n🧹 Cleaning up remaining drones...")
            self.cleanup_all()

def main():
    test = MasterDeathTest()
    
    # Set up signal handler for clean exit
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down test...")
        test.cleanup_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    test.run_test()

if __name__ == "__main__":
    print("💀 Master Death Detection Test")
    print("This test verifies that drones properly detect master death and re-elect")
    print("\nRun 'python3 network_monitor.py' in another terminal to watch the network status")
    print("Press Ctrl+C to exit at any time\n")
    
    input("Press Enter to start the test...")
    main()