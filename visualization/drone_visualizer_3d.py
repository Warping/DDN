#!/usr/bin/env python3
"""
3D Real-Time Drone Network Visualizer

This module provides a real-time 3D visualization of the drone network using matplotlib.
Drones are displayed as colored dots at their actual positions with different colors
representing different states (seeking, connected, master, slave).

The visualizer operates as a passive monitor - it observes the network through RNS
packet monitoring and updates the 3D plot in real-time.
"""

import os
import sys
import threading
import time
import json
from typing import Dict, List, Optional, Tuple
import numpy as np

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import RNS
from core.drone_state import DroneStatus, DroneState

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.animation as animation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("❌ Matplotlib not available. Please install with: pip install matplotlib")
    sys.exit(1)

class PassiveBroadcastHandler:
    """
    Broadcast handler for listening to drone packets
    """
    
    def __init__(self):
        self.packet_buffer = []
        
        # Initialize RNS with proper config path
        try:
            # Use the same config path as the drones
            self.reticulum = RNS.Reticulum("../.reticulum_config")
            print("✅ RNS initialized successfully for 3D visualizer")
        except Exception as e:
            print(f"⚠️  RNS initialization warning: {e}")
            try:
                # Try without config path
                self.reticulum = RNS.Reticulum()
                print("✅ RNS initialized with default config")
            except Exception as e2:
                print(f"❌ RNS initialization failed: {e2}")
                self.reticulum = None
        
        # Create the destination for listening
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
                lambda data, packet: self.packet_buffer.append((time.time(), data, packet))
            )
            print("✅ Broadcast destination created for 3D visualization")
        except Exception as e:
            print(f"❌ Error creating broadcast destination: {e}")
            self.broadcast_destination = None
    
    def get_packet(self):
        if len(self.packet_buffer) > 0:
            return self.packet_buffer.pop(0)
        else:
            return None

class DroneData:
    """
    Simple drone data container for 3D visualization
    """
    
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.position = None
        self.old_position = None
        self.status = DroneStatus.CONNECTED
        self.last_seen = time.time()
        self.battery_level = 100.0
        
    def update(self, position=None, status=None, battery_level=None):
        if position:
            if self.position != position:
                self.old_position = self.position
            self.position = position
        if status:
            self.status = status
        if battery_level is not None:
            self.battery_level = battery_level
        self.last_seen = time.time()
    
    def is_online(self, timeout=5.0):
        return (time.time() - self.last_seen) < timeout

class Drone3DVisualizer:
    """
    Real-time 3D drone network visualizer using matplotlib
    """
    
    def __init__(self):
        self.drones: Dict[int, DroneData] = {}
        self.broadcast_handler = PassiveBroadcastHandler()
        self.running = False
        self.monitor_thread = None
        
        # Visualization settings
        self.colors = {
            DroneStatus.SEEKING: '#FF8C00',     # Dark Orange
            DroneStatus.CONNECTED: '#32CD32',   # Lime Green  
            DroneStatus.MASTER: '#FF1493',      # Deep Pink
            DroneStatus.SLAVE: '#1E90FF',       # Dodger Blue
            DroneStatus.OFFLINE: '#696969',     # Dim Gray
            DroneStatus.LOST: '#DC143C'         # Crimson
        }
        
        self.markers = {
            DroneStatus.SEEKING: 'o',      # Circle
            DroneStatus.CONNECTED: 's',    # Square
            DroneStatus.MASTER: '^',       # Triangle up
            DroneStatus.SLAVE: 'D',        # Diamond
            DroneStatus.OFFLINE: 'x',      # X
            DroneStatus.LOST: 'P'          # Plus
        }
        
        # Plot settings
        self.fig = None
        self.ax = None
        self.scatter_plots = {}
        self.text_annotations = {}
        self.animation = None
        
        # Data for plotting
        self.plot_data = {status: {'x': [], 'y': [], 'z': [], 'ids': []} 
                         for status in DroneStatus}
        
    def start_monitoring(self):
        """Start monitoring drone packets"""
        if self.running:
            return
            
        self.running = True
        
        if not self.broadcast_handler.broadcast_destination:
            print("❌ Cannot start monitoring - broadcast handler failed to initialize")
            return
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_packets, daemon=True)
        self.monitor_thread.start()
        
        print("🔍 3D visualization monitoring started...")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("🛑 3D monitoring stopped")
    
    def _monitor_packets(self):
        """Monitor incoming packets in background thread"""
        packet_count = 0
        while self.running:
            try:
                if self.broadcast_handler:
                    packet_info = self.broadcast_handler.get_packet()
                    if packet_info:
                        packet_count += 1
                        timestamp, data, packet = packet_info
                        self._process_packet(data, timestamp)
                        
                        if packet_count <= 3:  # Show first few packets for debugging
                            print(f"📦 3D Visualizer received packet #{packet_count}")
                    else:
                        time.sleep(0.05)  # Faster polling for real-time visualization
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ 3D Packet processing error: {e}")
                time.sleep(0.1)
        
        # Clean up old drones periodically
        self._cleanup_old_drones()
    
    def _process_packet(self, data, timestamp):
        """Process received drone packet"""
        try:
            # Parse JSON packet
            json_str = data.decode('utf-8')
            packet_data = json.loads(json_str)
            
            drone_id = packet_data.get("drone_id")
            action = packet_data.get("action", "")
            params = packet_data.get("params", {})
            current_state = packet_data.get("current_state", "CONNECTED")
            
            if drone_id is None:
                return
            
            # Extract drone information
            position = params.get("position", None)
            battery_level = params.get("battery_level", None)
            
            # Parse status
            status = self._parse_status(current_state, action)
            
            # Update or create drone
            if drone_id not in self.drones:
                self.drones[drone_id] = DroneData(drone_id)
                print(f"🆕 New drone detected: {drone_id}")
            
            self.drones[drone_id].update(
                position=position,
                status=status,
                battery_level=battery_level
            )
            
        except Exception as e:
            # Silently ignore malformed packets
            pass
    
    def _parse_status(self, status_str, action=""):
        """Parse status string to DroneStatus enum"""
        try:
            # Handle common status strings
            status_map = {
                "seeking": DroneStatus.SEEKING,
                "connected": DroneStatus.CONNECTED,
                "master": DroneStatus.MASTER,
                "slave": DroneStatus.SLAVE,
                "offline": DroneStatus.OFFLINE,
                "lost": DroneStatus.LOST
            }
            
            # Check action for additional context
            if action in ["DISCOVERY_ANNOUNCE", "DISCOVERY_RESPONSE"]:
                return DroneStatus.SEEKING
            
            return status_map.get(status_str.lower(), DroneStatus.CONNECTED)
        except:
            return DroneStatus.CONNECTED
    
    def _cleanup_old_drones(self):
        """Remove drones that haven't been seen recently"""
        current_time = time.time()
        old_drones = [drone_id for drone_id, drone in self.drones.items() 
                      if not drone.is_online(timeout=10.0)]
        
        for drone_id in old_drones:
            print(f"🗑️ Removing stale drone: {drone_id}")
            del self.drones[drone_id]
    
    def _update_plot_data(self):
        """Update plot data structures"""
        # Clear previous data
        for status in DroneStatus:
            self.plot_data[status] = {'x': [], 'y': [], 'z': [], 'ids': []}
        
        # Group drones by status
        for drone in self.drones.values():
            if drone.is_online():
                status = drone.status
                x, y, z = drone.position
                
                self.plot_data[status]['x'].append(x)
                self.plot_data[status]['y'].append(y) 
                self.plot_data[status]['z'].append(z)
                self.plot_data[status]['ids'].append(drone.drone_id)
    
    def _init_plot(self):
        """Initialize the 3D plot"""
        self.fig = plt.figure(figsize=(12, 9))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set up the plot
        self.ax.set_xlabel('X Position (m)')
        self.ax.set_ylabel('Y Position (m)')
        self.ax.set_zlabel('Z Position (m)')
        self.ax.set_title('Real-Time 3D Drone Network Visualization')
        
        # Set fixed limits
        self.ax.set_xlim([-5, 5])
        self.ax.set_ylim([-5, 5])
        self.ax.set_zlim([0, 10])
        
        # Initialize scatter plots with placeholder data
        self.scatter_plots = {}
        # We'll create new scatter plots in each update rather than reusing them
        
        # Add legend
        self.ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        
        # Add grid
        self.ax.grid(True, alpha=0.3)
        
        return self.scatter_plots.values()
    
    def _update_plot(self, frame):
        """Update function for animation"""
        if not self.ax:
            return []
            
        self._update_plot_data()
        
        # Clear the axes and redraw everything
        self.ax.clear()
        
        # Reset axis properties
        self.ax.set_xlabel('X Position (m)')
        self.ax.set_ylabel('Y Position (m)')
        self.ax.set_zlabel('Z Position (m)')
        self.ax.grid(True, alpha=0.3)
        
        # Create scatter plots for each status with data
        scatter_artists = []
        legend_handles = []
        
        for status in DroneStatus:
            data = self.plot_data[status]
            
            if data['x'] and data['y'] and data['z']:  # Only plot if there's data
                # Create scatter plot for this status
                scatter = self.ax.scatter(
                    data['x'], data['y'], data['z'],  # type: ignore
                    c=self.colors[status],
                    marker=self.markers[status],
                    s=150,  # Large dots for visibility
                    alpha=0.8,
                    label=f'{status.value.title()}',
                    edgecolors='black',
                    linewidth=1
                )
                scatter_artists.append(scatter)
                legend_handles.append(scatter)
                
                # Add drone ID labels
                for i, drone_id in enumerate(data['ids']):
                    x, y, z = data['x'][i], data['y'][i], data['z'][i]
                    self.ax.text(x, y, z, f'  {drone_id}', 
                               fontsize=10, alpha=0.9, weight='bold')
        
        # Add legend if we have any data
        if legend_handles:
            self.ax.legend(handles=legend_handles, loc='upper right', bbox_to_anchor=(1.15, 1))
        
        # Update title with drone count
        online_count = len([d for d in self.drones.values() if d.is_online()])
        master_count = len([d for d in self.drones.values() 
                           if d.is_online() and d.status == DroneStatus.MASTER])
        
        title = f'Real-Time 3D Drone Network - {online_count} Online'
        if master_count > 0:
            masters = [d.drone_id for d in self.drones.values() 
                      if d.is_online() and d.status == DroneStatus.MASTER]
            title += f' | Master: {masters[0] if masters else "None"}'
        
        self.ax.set_title(title)
        
        # Set fixed limits - no auto-scaling
        self.ax.set_xlim([-5, 5])
        self.ax.set_ylim([-5, 5])
        self.ax.set_zlim([0, 10])
        
        return scatter_artists
    
    def start_visualization(self, update_interval=1000):
        """Start the real-time 3D visualization"""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ Matplotlib not available - cannot start 3D visualization")
            return
        
        print("🚁 Starting Real-Time 3D Drone Network Visualization")
        print("Press Ctrl+C in terminal to exit")
        
        # Start monitoring
        self.start_monitoring()
        
        # Wait a moment for initial data
        time.sleep(2)
        
        # Initialize plot
        artists = self._init_plot()
        
        # Set up animation only if fig is initialized
        if self.fig:
            self.animation = animation.FuncAnimation(
                self.fig, 
                self._update_plot,
                interval=update_interval,  # Update every 1000ms (1 second)
                blit=False,
                cache_frame_data=False
            )
        
        # Show plot
        plt.tight_layout()
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n🛑 Stopping 3D visualization...")
        finally:
            self.stop_monitoring()

def main():
    """Main function for 3D drone visualization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-Time 3D Drone Network Visualizer")
    parser.add_argument("--update-interval", type=int, default=1000,
                       help="Update interval in milliseconds (default: 1000)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ This visualizer requires matplotlib.")
        print("Install it with: pip install matplotlib")
        return
    
    print("🚁 Initializing 3D Drone Network Visualizer...")
    
    # Create visualizer
    visualizer = Drone3DVisualizer()
    
    try:
        # Start visualization
        visualizer.start_visualization(update_interval=args.update_interval)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down 3D visualizer...")
    except Exception as e:
        print(f"❌ Error in 3D visualizer: {e}")
        import traceback
        if args.debug:
            traceback.print_exc()
    finally:
        visualizer.stop_monitoring()

if __name__ == "__main__":
    main()