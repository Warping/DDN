#!/usr/bin/env python3
"""
Drone Network Visualizer

This module provides various ways to visualize the drone network:
1. Real-time terminal display
2. Network topology diagram
3. 3D position plot (if matplotlib available)
4. Web-based dashboard (if Flask available)

This visualizer operates as a passive monitor - it doesn't spawn its own drone
but observes the network through RNS packet monitoring.
"""

import time
import json
import os
import sys
import threading
from typing import Dict, List, Optional, Tuple
import RNS
from drone_state import DroneNetwork, DroneStatus, DroneState
from drone_packet import DronePacket

class PassiveBroadcastHandler:
    """
    Modified broadcast handler that doesn't reinitialize RNS
    """
    
    def __init__(self):
        self.packet_buffer = []
        
        # Don't initialize RNS - assume it's already running
        # Just create the destination for listening
        try:
            self.broadcast_destination = RNS.Destination(
                None,
                RNS.Destination.IN,
                RNS.Destination.PLAIN,
                "example_utilities",
                "broadcast",
                "public_information"
            )
            
            # Set up packet callback
            self.broadcast_destination.set_packet_callback(
                lambda data, packet: self.packet_buffer.append((time.monotonic_ns(), data, packet))
            )
        except Exception as e:
            print(f"⚠️  Warning: Could not create broadcast destination: {e}")
            self.broadcast_destination = None
    
    def get_packet(self):
        if len(self.packet_buffer) > 0:
            return self.packet_buffer.pop(0)
        else:
            return None

class PassiveNetworkState:
    """
    Passive network state that tracks observed drones without a self drone
    """
    
    def __init__(self):
        self.known_drones: Dict[int, DroneState] = {}
        self.master_drone_id: Optional[int] = None
        self.network_established = False
        
    def add_or_update_drone(self, drone_id: int, status: Optional[DroneStatus] = None, 
                           position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                           battery_level: float = 100.0, signal_strength: float = 0.0):
        """Add a new drone or update existing drone information"""
        
        if status is None:
            status = DroneStatus.CONNECTED
            
        if drone_id in self.known_drones:
            # Update existing drone
            drone = self.known_drones[drone_id]
            drone.status = status
            drone.update_position(*position)
            drone.update_battery(battery_level)
            drone.signal_strength = signal_strength
            drone.update_last_seen()
        else:
            # Add new drone
            drone = DroneState(drone_id)
            drone.status = status
            drone.update_position(*position)
            drone.update_battery(battery_level)
            drone.signal_strength = signal_strength
            self.known_drones[drone_id] = drone
            
        return drone
    
    def get_all_drones(self):
        """Get list of all known drones"""
        return list(self.known_drones.values())
    
    def get_online_drones(self, timeout: float = 30.0):
        """Get list of all online drones"""
        return [drone for drone in self.known_drones.values() if drone.is_online(timeout)]
    
    def get_drone_count(self) -> int:
        """Get total number of known drones"""
        return len(self.known_drones)
    
    def get_online_drone_count(self, timeout: float = 30.0) -> int:
        """Get number of online drones"""
        return len(self.get_online_drones(timeout))
    
    def get_discovery_status(self) -> str:
        """Get a human-readable discovery status"""
        online_count = self.get_online_drone_count()
        total_count = self.get_drone_count()
        
        if online_count == 0:
            return "No drones detected"
        elif online_count == 1:
            return f"Found {online_count} drone"
        else:
            master_status = f"Master: {self.master_drone_id}" if self.master_drone_id else "No master"
            return f"Network detected: {online_count} drones online. {master_status}"
    
    def get_self_id(self) -> Optional[int]:
        """Get self ID - None for passive monitor"""
        return None
    
    def get_network_topology(self) -> Dict:
        """Get a representation of the network topology"""
        return {
            "self_drone_id": None,  # No self drone in passive mode
            "master_drone_id": self.master_drone_id,
            "total_drones": self.get_drone_count(),
            "online_drones": self.get_online_drone_count(),
            "network_established": self.network_established,
            "drones": {drone_id: drone.to_dict() for drone_id, drone in self.known_drones.items()}
        }

class PassiveNetworkMonitor:
    """
    Passive monitor that observes drone network without participating
    """
    
    def __init__(self):
        # Use passive network state instead of DroneNetwork
        self.drone_network = PassiveNetworkState()
        self.running = False
        self.broadcast_handler = None
        self.monitor_thread = None
        self.last_activity = {}  # Track last activity time for each drone
        
        # Initialize RNS only if not already initialized
        try:
            RNS.Reticulum()
        except OSError as e:
            if "already running" in str(e):
                # RNS is already initialized, which is fine
                pass
            else:
                raise
        
    def start_monitoring(self):
        """Start passive monitoring of the network"""
        if self.running:
            return
            
        self.running = True
        
        # Set up broadcast handler to listen for drone packets
        self.broadcast_handler = PassiveBroadcastHandler()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_packets, daemon=True)
        self.monitor_thread.start()
        
        print("🔍 Passive network monitoring started...")
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("🛑 Monitoring stopped")
        
    def _monitor_packets(self):
        """Monitor incoming packets in background thread"""
        while self.running:
            try:
                if self.broadcast_handler:
                    packet_info = self.broadcast_handler.get_packet()
                    if packet_info:
                        timestamp, data, packet = packet_info
                        self._process_packet(data, timestamp)
                    else:
                        time.sleep(0.1)  # Small delay when no packets
                else:
                    time.sleep(0.1)
            except Exception as e:
                # Silently handle errors to avoid spam
                time.sleep(0.1)
        
    def _process_packet(self, data, timestamp):
        """Process received packet data"""
        try:
            # Try to parse as JSON
            json_str = data.decode('utf-8')
            packet_data = json.loads(json_str)
            
            drone_id = packet_data.get("drone_id")
            action = packet_data.get("action", "")
            params = packet_data.get("params", {})
            current_state = packet_data.get("current_state", "UNKNOWN")
            
            if drone_id is None:
                return
                
            # Update last activity
            self.last_activity[drone_id] = time.time()
            
            # Extract position (default to origin if not provided)
            position = params.get("position", (0, 0, 0))
            battery_level = params.get("battery_level", 100.0)
            
            # Convert state string to DroneStatus enum
            try:
                if action in ["DISCOVERY_ANNOUNCE", "DISCOVERY_RESPONSE"]:
                    status = DroneStatus.SEEKING
                elif action == "HEARTBEAT":
                    status = self._parse_status(current_state)
                elif action == "NETWORK_STATUS":
                    status = DroneStatus.MASTER  # Usually master sends network status
                    # Process known drones from network status
                    self._process_network_status(params)
                else:
                    status = self._parse_status(current_state)
            except:
                status = DroneStatus.CONNECTED
            
            # Update drone info in our network model
            self.drone_network.add_or_update_drone(
                drone_id, 
                status, 
                position, 
                battery_level
            )
                
        except Exception as e:
            # Silently ignore malformed packets
            pass
    
    def _parse_status(self, status_str):
        """Parse status string to DroneStatus enum"""
        try:
            # Handle common status strings
            status_map = {
                "SEEKING": DroneStatus.SEEKING,
                "CONNECTED": DroneStatus.CONNECTED,
                "MASTER": DroneStatus.MASTER,
                "SLAVE": DroneStatus.SLAVE,
                "OFFLINE": DroneStatus.OFFLINE,
                "LOST": DroneStatus.LOST
            }
            return status_map.get(status_str.upper(), DroneStatus.CONNECTED)
        except:
            return DroneStatus.CONNECTED
    
    def _process_network_status(self, params):
        """Process network status information"""
        try:
            known_drones = params.get("known_drones", [])
            master_id = params.get("master_id")
            
            if master_id and hasattr(self.drone_network, 'master_drone_id'):
                self.drone_network.master_drone_id = master_id
                
            # Update information about known drones
            for drone_info in known_drones:
                if isinstance(drone_info, dict):
                    drone_id = drone_info.get("id")
                    position = drone_info.get("position", (0, 0, 0))
                    status_str = drone_info.get("status", "CONNECTED")
                    battery_level = drone_info.get("battery_level", 100.0)
                    
                    if drone_id:
                        status = self._parse_status(status_str)
                        self.drone_network.add_or_update_drone(
                            drone_id, 
                            status, 
                            position, 
                            battery_level
                        )
        except:
            pass
    
    def cleanup_stale_drones(self, timeout=3):
        """Remove drones that haven't been seen for a while"""
        current_time = time.time()
        stale_drones = []
        
        for drone_id, last_seen in self.last_activity.items():
            if current_time - last_seen > timeout:
                stale_drones.append(drone_id)
        
        for drone_id in stale_drones:
            if hasattr(self.drone_network, 'known_drones') and drone_id in self.drone_network.known_drones:
                del self.drone_network.known_drones[drone_id]
            if drone_id in self.last_activity:
                del self.last_activity[drone_id]

class DroneNetworkVisualizer:
    """
    Visualizes drone network state in various formats
    """
    
    def __init__(self, monitor: PassiveNetworkMonitor):
        self.monitor = monitor
        self.network = monitor.drone_network
        self.update_interval = 1.0  # Update every second
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_status_symbol(self, status: DroneStatus) -> str:
        """Get visual symbol for drone status"""
        symbols = {
            DroneStatus.OFFLINE: "⚫",
            DroneStatus.SEEKING: "🔍",
            DroneStatus.CONNECTED: "🟢",
            DroneStatus.MASTER: "👑",
            DroneStatus.SLAVE: "🔵",
            DroneStatus.LOST: "❌"
        }
        return symbols.get(status, "❓")
    
    def format_position(self, position: tuple) -> str:
        """Format position coordinates"""
        x, y, z = position
        return f"({x:6.1f}, {y:6.1f}, {z:6.1f})"
    
    def format_battery(self, level: float) -> str:
        """Format battery level with visual indicator"""
        if level >= 80:
            return f"🔋{level:5.1f}%"
        elif level >= 50:
            return f"🔋{level:5.1f}%"
        elif level >= 20:
            return f"🪫{level:5.1f}%"
        else:
            return f"🪫{level:5.1f}%"
    
    def print_network_overview(self):
        """Print network overview header"""
        print("=" * 80)
        print("🚁 DRONE NETWORK VISUALIZATION (PASSIVE MODE) 🚁")
        print("=" * 80)
        
        # Network summary
        online_count = self.network.get_online_drone_count()
        total_count = self.network.get_drone_count()
        
        print(f"📊 Network Status: {self.network.get_discovery_status()}")
        print(f"🌐 Total Drones: {total_count} | Online: {online_count}")
        print("🔍 Mode: Passive Observer")
        
        if hasattr(self.network, 'master_drone_id') and self.network.master_drone_id:
            print(f"👑 Master: {self.network.master_drone_id}")
        else:
            print("👑 Master: None")
            
        print("-" * 80)
    
    def print_drone_table(self):
        """Print detailed drone information table"""
        drones = self.network.get_all_drones()
        
        # Table header
        print(f"{'ID':>6} {'Status':>8} {'Position':>20} {'Battery':>10} {'Reliability':>12} {'Last Seen':>12}")
        print("-" * 80)
        
        # Sort drones by ID for consistent display
        sorted_drones = sorted(drones, key=lambda d: d.drone_id)
        
        for drone in sorted_drones:
            # Status with symbol
            status_display = f"{self.get_status_symbol(drone.status)} {drone.status.value[:6]}"
            
            # Position
            position_str = self.format_position(drone.position)
            
            # Battery
            battery_str = self.format_battery(drone.battery_level)
            
            # Reliability score
            reliability = drone.get_reliability_score()
            reliability_str = f"{reliability:>6.1%}"
            
            # Last seen (time ago)
            time_ago = time.time() - drone.last_seen
            if time_ago < 60:
                last_seen = f"{time_ago:4.0f}s"
            elif time_ago < 3600:
                last_seen = f"{time_ago/60:4.0f}m"
            else:
                last_seen = f"{time_ago/3600:4.0f}h"
            
            # Mark self drone
            self_marker = "→" if drone.is_self else " "
            
            print(f"{self_marker}{drone.drone_id:>5} {status_display:>10} {position_str:>20} {battery_str:>10} {reliability_str:>12} {last_seen:>12}")
    
    def print_network_topology(self):
        """Print ASCII network topology"""
        print("\n📡 Network Topology:")
        print("-" * 40)
        
        online_drones = self.network.get_online_drones()
        
        if not online_drones:
            print("   No drones online")
            return
        
        # Group drones by status
        master_drones = [d for d in online_drones if d.status == DroneStatus.MASTER]
        slave_drones = [d for d in online_drones if d.status == DroneStatus.SLAVE]
        connected_drones = [d for d in online_drones if d.status == DroneStatus.CONNECTED]
        seeking_drones = [d for d in online_drones if d.status == DroneStatus.SEEKING]
        
        # Display hierarchy
        if master_drones:
            for master in master_drones:
                marker = "🔸" if master.is_self else "🔹"
                print(f"   👑 Master: {marker} Drone {master.drone_id}")
                
                if slave_drones:
                    for i, slave in enumerate(slave_drones):
                        marker = "🔸" if slave.is_self else "🔹"
                        connector = "└──" if i == len(slave_drones) - 1 else "├──"
                        print(f"   {connector} Slave: {marker} Drone {slave.drone_id}")
        
        if connected_drones:
            print("   🔗 Connected:")
            for drone in connected_drones:
                marker = "🔸" if drone.is_self else "🔹"
                print(f"      • {marker} Drone {drone.drone_id}")
        
        if seeking_drones:
            print("   🔍 Seeking:")
            for drone in seeking_drones:
                marker = "🔸" if drone.is_self else "🔹"
                print(f"      • {marker} Drone {drone.drone_id}")
    
    def print_statistics(self):
        """Print network statistics"""
        print("\n📈 Network Statistics:")
        print("-" * 40)
        
        drones = self.network.get_all_drones()
        
        if not drones:
            print("   No data available")
            return
        
        # Calculate statistics
        total_pings = sum(d.ping_count for d in drones)
        total_responses = sum(d.response_count for d in drones)
        avg_battery = sum(d.battery_level for d in drones) / len(drones)
        
        # Network reliability
        network_reliability = total_responses / total_pings if total_pings > 0 else 1.0
        
        print(f"   Average Battery: {avg_battery:5.1f}%")
        print(f"   Network Reliability: {network_reliability:5.1%}")
        print(f"   Total Messages: {total_pings} pings, {total_responses} responses")
        print(f"   Network Age: {time.time() - min(d.discovery_time for d in drones):6.0f}s")
    
    def real_time_display(self):
        """Display real-time network visualization in terminal"""
        print("🚁 Starting Real-Time Drone Network Visualization (Passive Mode)")
        print("Press Ctrl+C to exit\n")
        
        # Start monitoring if not already started
        if not self.monitor.running:
            self.monitor.start_monitoring()
        
        try:
            while True:
                self.clear_screen()
                
                # Clean up stale drones periodically
                self.monitor.cleanup_stale_drones()
                
                # Display visualization
                self.print_network_overview()
                self.print_drone_table()
                self.print_network_topology()
                self.print_statistics()
                
                print(f"\n⏱️  Last updated: {time.strftime('%H:%M:%S')}")
                print("Press Ctrl+C to exit")
                
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping visualization...")
            self.monitor.stop_monitoring()
    
    def export_network_data(self, filename: Optional[str] = None):
        """Export current network state to JSON file"""
        if filename is None:
            filename = f"drone_network_{int(time.time())}.json"
        
        topology = self.network.get_network_topology()
        
        # Add timestamp and additional metadata
        export_data = {
            "timestamp": time.time(),
            "export_time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "network_topology": topology,
            "statistics": {
                "total_drones": self.network.get_drone_count(),
                "online_drones": self.network.get_online_drone_count(),
                "network_age": time.time() - min(d.discovery_time for d in self.network.get_all_drones()) if self.network.get_all_drones() else 0
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"📄 Network data exported to: {filename}")
        return filename

class SimpleDroneMonitor:
    """
    Simplified monitor that can be embedded in your main control loop
    """
    
    def __init__(self, monitor: PassiveNetworkMonitor):
        self.monitor = monitor
        self.network = monitor.drone_network
        self.last_display_time = 0
        self.display_interval = 10.0  # Display every 10 seconds
        
        # Start monitoring if not already started
        if not self.monitor.running:
            self.monitor.start_monitoring()
    
    def should_display(self) -> bool:
        """Check if it's time to display status"""
        return (time.time() - self.last_display_time) >= self.display_interval
    
    def display_compact_status(self):
        """Display compact network status"""
        if not self.should_display():
            return
        
        online_count = self.network.get_online_drone_count()
        total_count = self.network.get_drone_count()
        
        drones_str = []
        for drone in self.network.get_online_drones():
            status_symbol = {
                DroneStatus.SEEKING: "🔍",
                DroneStatus.CONNECTED: "🟢", 
                DroneStatus.MASTER: "👑",
                DroneStatus.SLAVE: "🔵"
            }.get(drone.status, "❓")
            
            self_marker = "*" if drone.is_self else ""
            drones_str.append(f"{drone.drone_id}{status_symbol}{self_marker}")
        
        print(f"🚁 Network: {online_count}/{total_count} online | Drones: {', '.join(drones_str)} | Status: {self.network.get_discovery_status()}")
        
        self.last_display_time = time.time()

def create_matplotlib_visualization(monitor: PassiveNetworkMonitor):
    """Create 3D matplotlib visualization of drone positions"""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        drones = monitor.drone_network.get_all_drones()
        
        # Separate data by status
        positions = {'seeking': [], 'connected': [], 'master': [], 'slave': []}
        colors = {'seeking': 'orange', 'connected': 'green', 'master': 'red', 'slave': 'blue'}
        markers = {'seeking': 'o', 'connected': 's', 'master': '^', 'slave': 'D'}
        
        for drone in drones:
            x, y, z = drone.position
            
            # Categorize by status
            if drone.status == DroneStatus.SEEKING:
                positions['seeking'].append([x, y, z, drone.drone_id])
            elif drone.status == DroneStatus.CONNECTED:
                positions['connected'].append([x, y, z, drone.drone_id])
            elif drone.status == DroneStatus.MASTER:
                positions['master'].append([x, y, z, drone.drone_id])
            elif drone.status == DroneStatus.SLAVE:
                positions['slave'].append([x, y, z, drone.drone_id])
        
        # Plot each group
        for status, pos_list in positions.items():
            if pos_list:
                pos_array = np.array(pos_list)
                ax.scatter(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], 
                          c=colors[status], marker=markers[status], s=100, label=status.title())
                
                # Add drone ID labels
                for i, (x, y, z, drone_id) in enumerate(pos_list):
                    ax.text(x, y, z, f'  {int(drone_id)}', fontsize=8)
        
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        ax.set_zlabel('Z Position')
        ax.set_title('Drone Network 3D Visualization')
        ax.legend()
        
        plt.tight_layout()
        plt.show()
        
        return True
        
    except ImportError:
        print("📊 Matplotlib not available. Install with: pip install matplotlib")
        return False

def main():
    """Main function for standalone visualization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Drone Network Visualizer (Passive Mode)")
    parser.add_argument("--mode", choices=['realtime', 'plot', 'export'], default='realtime',
                       help="Visualization mode")
    parser.add_argument("--export-file", type=str, help="Export filename")
    parser.add_argument("--update-interval", type=float, default=1.0, 
                       help="Update interval in seconds")
    
    args = parser.parse_args()
    
    print("🚁 Initializing Passive Drone Network Visualizer...")
    
    # Create passive monitor
    monitor = PassiveNetworkMonitor()
    
    # Create visualizer
    visualizer = DroneNetworkVisualizer(monitor)
    visualizer.update_interval = args.update_interval
    
    if args.mode == 'realtime':
        print("Starting real-time visualization...")
        visualizer.real_time_display()
    
    elif args.mode == 'plot':
        print("Creating 3D plot...")
        if not create_matplotlib_visualization(monitor):
            print("Falling back to terminal visualization...")
            visualizer.real_time_display()
    
    elif args.mode == 'export':
        print("Exporting network data...")
        # Start monitoring briefly to collect data
        monitor.start_monitoring()
        time.sleep(5)  # Collect data for 5 seconds
        filename = visualizer.export_network_data(args.export_file)
        monitor.stop_monitoring()
        print(f"Data exported to: {filename}")

if __name__ == "__main__":
    main()