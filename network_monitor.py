#!/usr/bin/env python3
"""
Network Status Monitor

Simple script to monitor the current state of the drone network.
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from drone_state import DroneNetwork
from drone_visualizer import PassiveBroadcastHandler

class NetworkStatusMonitor:
    def __init__(self):
        self.network = DroneNetwork()
        self.broadcast_handler = PassiveBroadcastHandler()
        # Manual packet processing since set_network doesn't exist
        self.last_status_count = 0
        
    def display_status(self):
        """Display current network status"""
        print("\n" + "="*60)
        print(f"🌐 NETWORK STATUS - {time.strftime('%H:%M:%S')}")
        print("="*60)
        
        if not self.network.known_drones:
            print("📡 No drones detected in network")
            return
        
        # Sort drones by ID for consistent display
        sorted_drones = sorted(self.network.known_drones.values(), key=lambda d: d.drone_id)
        
        print(f"📊 Total Drones: {len(sorted_drones)}")
        print(f"👑 Master: {self.network.master_drone_id or 'None'}")
        print(f"🗳️  Election Active: {getattr(self.network, 'election_in_progress', False)}")
        print()
        
        # Display each drone
        for drone in sorted_drones:
            status_icon = "👑" if drone.drone_id == self.network.master_drone_id else "🤖"
            role = "MASTER" if drone.drone_id == self.network.master_drone_id else "SLAVE"
            
            print(f"{status_icon} Drone {drone.drone_id:>4} | {role:<6} | "
                  f"Battery: {drone.battery_level:>3}% | "
                  f"Last seen: {time.time() - drone.last_seen:.1f}s ago")
        
        # Show network statistics
        if len(sorted_drones) > 1:
            avg_battery = sum(d.battery_level for d in sorted_drones) / len(sorted_drones)
            print(f"\n📈 Average Battery: {avg_battery:.1f}%")
            
        # Show recent activity
        current_count = len(self.network.known_drones)
        if current_count != self.last_status_count:
            if current_count > self.last_status_count:
                print(f"📈 Network grew (+{current_count - self.last_status_count})")
            else:
                print(f"📉 Network shrunk ({current_count - self.last_status_count})")
            self.last_status_count = current_count
    
    def run(self):
        """Run the monitor"""
        print("🚁 DRONE NETWORK STATUS MONITOR")
        print("Press Ctrl+C to exit")
        print("Run 'python master_election_demo.py' in another terminal to see activity")
        
        try:
            while True:
                self.display_status()
                time.sleep(1)  # Update every 1 second - increased from 3 seconds
                
        except KeyboardInterrupt:
            print("\n👋 Monitor stopped")

if __name__ == "__main__":
    monitor = NetworkStatusMonitor()
    monitor.run()