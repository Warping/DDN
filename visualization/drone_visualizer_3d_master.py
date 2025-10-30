#!/usr/bin/env python3
"""
Master-Based 3D Real-Time Drone Network Visualizer

This module provides a real-time 3D visualization of the drone network using matplotlib,
relying solely on network status packets from the master drone. This ensures all drones
are displayed at their correct positions as known by the master.

The visualizer filters for NETWORK_STATUS packets from the current master drone and us                            status_enum = DroneStatus.MASTER if str(drone_id) == str(master_id) else DroneStatus.SLAVEs
the position data from these packets to update the 3D visualization.
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
from core.drone_state import DroneStatus
from controllers.enhanced_state_controller import EnhancedStateController

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
    Broadcast handler for listening to drone packets, focused on master network status
    """
    
    def __init__(self):
        self.packet_buffer = []
        
        # Initialize RNS with proper config path
        try:
            # Use the same config path as the drones
            self.reticulum = RNS.Reticulum("../.reticulum_config")
            # Get MTU from config if available
            mtu = self.reticulum.MTU
            print(f"ℹ️  RNS MTU set to {mtu} bytes")
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
    
    def __init__(self, timeout, drone_id: int):
        self.drone_id = drone_id
        self.position = None
        self.old_position = None
        self.status = DroneStatus.CONNECTED
        self.last_seen = time.time()
        self.last_status_change = time.time()
        self.battery_level = 100.0
        self.signal_strength = 0.0
        self.offline_since = None  # Track when a drone went offline
        self.default_timeout = timeout  # Default timeout for online status
        
    def update(self, position=None, status=None, battery_level=None, signal_strength=None):
        if position:
            if self.position != position:
                self.old_position = self.position
            self.position = position
        if status:
            # Add debug output when status changes
            if self.status != status:
                print(f"📊 Drone {self.drone_id} status changed: {self.status.value} → {status.value}")
                
                # Track status change time
                self.last_status_change = time.time()
                
                # Track when drone goes offline
                if status == DroneStatus.OFFLINE and self.offline_since is None:
                    self.offline_since = time.time()
                elif status != DroneStatus.OFFLINE:
                    self.offline_since = None
                    
            self.status = status
        if battery_level is not None:
            self.battery_level = battery_level
        if signal_strength is not None:
            self.signal_strength = signal_strength
        
        # Only update last_seen if not going offline
        # This prevents resetting the timer for offline detection
        if status != DroneStatus.OFFLINE:
            self.last_seen = time.time()
    
    def is_online(self):
        return (time.time() - self.last_seen) < self.default_timeout

class MasterBasedDroneVisualizer:
    """
    Real-time 3D drone network visualizer that only uses master's network status packets
    """
    
    def __init__(self, timeout, debug_mode=False):
        self.drones: Dict[int, DroneData] = {}
        self.broadcast_handler = PassiveBroadcastHandler()
        self.running = False
        self.monitor_thread = None
        self.current_master_id = None
        self.last_update_time = 0
        self.last_master_packet_time = 0
        self.debug_mode = debug_mode  # Add debug mode flag
        self.default_timeout = timeout  # Seconds before a drone is considered offline
        
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
        
        # Message display
        self.info_text = None
        self.last_status_message = "Waiting for master drone..."
        
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
        
        print("🔍 3D visualization monitoring started, waiting for master network status packets...")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("🛑 3D monitoring stopped")
    
    def _monitor_packets(self):
        """Monitor incoming packets in background thread"""
        packet_count = 0
        master_packet_count = 0
        last_master_check = time.time()
        last_cleanup_check = time.time()
        
        while self.running:
            try:
                if self.broadcast_handler:
                    packet_info = self.broadcast_handler.get_packet()
                    if packet_info:
                        packet_count += 1
                        timestamp, data, packet = packet_info
                        if self._process_packet(data, timestamp):
                            master_packet_count += 1
                            if master_packet_count <= 3:
                                print(f"📊 Processed master network status packet #{master_packet_count}")
                    else:
                        time.sleep(0.05)  # Faster polling for real-time visualization
                else:
                    time.sleep(0.1)
                    
                # Periodically check for stale data
                current_time = time.time()
                
                # Every 5 seconds, actively check for master changes
                if current_time - last_master_check > 5.0:
                    last_master_check = current_time
                    # Reset our filter periodically to allow discovery of new masters
                    # This is important when we missed the master election packets
                    reset_time = getattr(self, 'master_reset_time', 10.0)
                    if self.current_master_id and current_time - self.last_master_packet_time > reset_time:
                        print(f"🔍 Actively searching for new master (no updates from {self.current_master_id} for {reset_time}s)")
                        self.current_master_id = None  # Reset master to allow discovery
                        
                    if self.debug_mode:
                        print(f"Debug: Current master: {self.current_master_id}, Time since last update: {current_time - self.last_master_packet_time:.1f}s")
                
                # Every 30 seconds, check for truly stale drones to remove
                if current_time - last_cleanup_check > 30.0:
                    last_cleanup_check = current_time
                    self._cleanup_very_old_drones(cleanup_timeout=60.0)  # Remove drones not seen for 60 seconds
                
                # Update status message for stale data
                if current_time - self.last_master_packet_time > 15.0:
                    # No master packet for 15 seconds, we may need to update the status message
                    if current_time - self.last_update_time > 2.0:  # Update message every 2 seconds
                        self.last_status_message = f"No master updates for {int(current_time - self.last_master_packet_time)}s"
                        self.last_update_time = current_time
                
            except Exception as e:
                print(f"⚠️ 3D Packet processing error: {e}")
                time.sleep(0.1)
    
    def _process_packet(self, data, timestamp):
        """
        Process received drone packet
        Returns True if it was a master network status packet and was processed
        """
        try:
            # Parse JSON packet
            json_str = data.decode('utf-8')
            packet_data = json.loads(json_str)
            
            drone_id = packet_data.get("drone_id")
            action = packet_data.get("action", "")
            params = packet_data.get("params", {})
            current_state = packet_data.get("current_state", "CONNECTED")
            
            # Handle master election announcement packets to track master changes
            if action == "ELECT_MASTER":
                candidate_id = params.get("candidate_id")
                if candidate_id:
                    print(f"⚠️ Master election in progress, candidate: {candidate_id}")
                    # Don't update master yet, but note that an election is happening
                    self.last_status_message = f"Master election in progress..."
                    self.last_update_time = time.time()
                    # No position updates, but mark that we're processing events
                    return True
            
            # Process network status packets to get position data
            if action != "NETWORK_STATUS":
                return False
                
            # Check if this is from a master drone or if it contains master_id info
            is_from_master = current_state.upper() == "MASTER"
            master_id_in_packet = params.get("master_id") or params.get("m")
            
            # Always update master if packet contains master_id information
            if master_id_in_packet and self.current_master_id != master_id_in_packet:
                print(f"🔄 Master change detected from network status: {master_id_in_packet}")
                self.current_master_id = master_id_in_packet
                # Clear drone data to rebuild from new master's perspective
                self.drones.clear()
            
            # If packet is not from master directly, we might still use it to find the master
            if not is_from_master and not self.current_master_id:
                if master_id_in_packet:
                    self.current_master_id = master_id_in_packet
                    print(f"🔄 Discovered master drone: {self.current_master_id}")
            
            # Accept packets from master or packets that contain network state from any drone
            # This helps us discover new masters and track changes
            process_packet = is_from_master or master_id_in_packet is not None
            
            # Only filter packets if we don't see master information
            if not process_packet and self.current_master_id and drone_id != self.current_master_id:
                return False
                
            # From this point, we know it's either from a master or contains useful network info
            self.last_master_packet_time = time.time()
            
            # If drone says it's master, update our current master
            if is_from_master:
                if self.current_master_id != drone_id:
                    print(f"👑 New master drone detected: {drone_id}")
                    self.current_master_id = drone_id
                    # Clear drone data to rebuild from new master's perspective
                    self.drones.clear()
                
                # Make sure this drone has the master status in our local data
                if drone_id in self.drones:
                    self.drones[drone_id].status = DroneStatus.MASTER
            
            # Update the status message
            self.last_status_message = f"Connected to master {self.current_master_id}"
            self.last_update_time = time.time()
            
            # Process drones from network status
            self._process_network_status(packet_data)
            return True
            
        except Exception as e:
            print(f"❌ Error processing packet: {e}")
            return False
    
    def _process_network_status(self, packet_data):
        """Process network status packet specifically"""
        try:
            drone_id = packet_data.get("drone_id")
            params = packet_data.get("params", {})
            
            # Process based on packet format
            # 1. Optimized format (priority - most bandwidth efficient)
            if "opt" in params and params.get("opt") and "d" in params:
                master_id = params.get("m")
                
                # Check if master has changed
                if master_id is not None and self.current_master_id != master_id:
                    print(f"🔄 Master updated from optimized packet: {master_id}")
                    self.current_master_id = master_id
                    # Clear drone data when master changes
                    self.drones.clear()
                
                # Add the master drone
                if master_id not in self.drones:
                    self.drones[master_id] = DroneData(self.default_timeout, master_id)
                self.drones[master_id].status = DroneStatus.MASTER
                self.drones[master_id].update()
                
                # Process optimized drone list
                opt_drones = params.get("d", [])
                for drone_info in opt_drones:
                    drone_id = drone_info.get('i')
                    position = drone_info.get('p')
                    
                    if drone_id and position:
                        if drone_id not in self.drones:
                            self.drones[drone_id] = DroneData(self.default_timeout, drone_id)
                        
                        # Set the appropriate status - if this is the master drone, mark as MASTER
                        status = DroneStatus.MASTER if str(drone_id) == str(master_id) else DroneStatus.SLAVE
                        self.drones[drone_id].update(
                            position=position,
                            status=status
                        )
            
            # 2. Positions-only format
            elif "positions_only" in params and params.get("positions_only") and "drones" in params:
                master_id = params.get("master_id")
                
                # Check if master has changed
                if master_id is not None and self.current_master_id != master_id:
                    print(f"🔄 Master updated from positions-only packet: {master_id}")
                    self.current_master_id = master_id
                    # Clear drone data when master changes
                    self.drones.clear()
                
                # Add the master drone
                if master_id not in self.drones:
                    self.drones[master_id] = DroneData(self.default_timeout, master_id)
                self.drones[master_id].status = DroneStatus.MASTER
                self.drones[master_id].update()
                
                # Process positions-only drone list
                position_drones = params.get("drones", [])
                for drone_info in position_drones:
                    drone_id = drone_info.get('id')
                    position = drone_info.get('pos')
                    
                    if drone_id and position:
                        if drone_id not in self.drones:
                            self.drones[drone_id] = DroneData(self.default_timeout, drone_id)
                        
                        # Set the appropriate status - if this is the master drone, mark as MASTER
                        status = DroneStatus.MASTER if str(drone_id) == str(master_id) else DroneStatus.SLAVE
                        self.drones[drone_id].update(
                            position=position,
                            status=status
                        )
            
            # 3. Compact format
            elif "compact_state" in params and params.get("compact_state") and "drones" in params:
                master_id = params.get("master_id")
                
                # Check if master has changed
                if master_id is not None and self.current_master_id != master_id:
                    print(f"🔄 Master updated from compact packet: {master_id}")
                    self.current_master_id = master_id
                    # Clear drone data when master changes
                    self.drones.clear()
                
                # Process compact drone list
                compact_drones = params.get("drones", [])
                for drone_info in compact_drones:
                    drone_id = drone_info.get('id')
                    status = drone_info.get('st')
                    position = drone_info.get('pos')
                    battery = drone_info.get('bat')
                    signal = drone_info.get('sig')
                    
                    if drone_id and position:
                        if drone_id not in self.drones:
                            self.drones[drone_id] = DroneData(self.default_timeout, drone_id)
                            
                        status_enum = DroneStatus.MASTER if drone_id == master_id else DroneStatus.SLAVE
                        if status:
                            try:
                                status_enum = DroneStatus(status)
                            except:
                                pass
                                
                        self.drones[drone_id].update(
                            position=position,
                            status=status_enum,
                            battery_level=battery,
                            signal_strength=signal
                        )
                        
            # 4. Original comprehensive format
            elif "known_drones" in params:
                network_state = params.get("known_drones", [])
                
                # Check if it's the comprehensive dictionary format
                if isinstance(network_state, dict) and 'all_drones' in network_state:
                    master_id = params.get("master_id")
                    
                    # Check if master has changed
                    if master_id is not None and self.current_master_id != master_id:
                        print(f"🔄 Master updated from comprehensive packet: {master_id}")
                        self.current_master_id = master_id
                        # Clear drone data when master changes
                        self.drones.clear()
                    
                    # Process comprehensive drone list
                    all_drones = network_state.get('all_drones', [])
                    for drone_info in all_drones:
                        drone_id = drone_info.get('drone_id')
                        status_str = drone_info.get('status')
                        position = drone_info.get('position')
                        battery = drone_info.get('battery_level')
                        signal = drone_info.get('signal_strength')
                        
                        if drone_id and position:
                            if drone_id not in self.drones:
                                self.drones[drone_id] = DroneData(self.default_timeout, drone_id)
                                
                            status_enum = DroneStatus.MASTER if str(drone_id) == str(master_id) else DroneStatus.SLAVE
                            if status_str:
                                try:
                                    status_enum = DroneStatus(status_str)
                                except:
                                    pass
                                    
                            self.drones[drone_id].update(
                                position=position,
                                status=status_enum,
                                battery_level=battery,
                                signal_strength=signal
                            )
        except Exception as e:
            print(f"❌ Error processing network status: {e}")
    
    def _update_plot_data(self):
        """Update plot data structures"""
        # Clear previous data
        for status in DroneStatus:
            self.plot_data[status] = {'x': [], 'y': [], 'z': [], 'ids': []}
            
        # Make sure master is shown with correct status
        # if self.current_master_id and self.current_master_id in self.drones:
        #     if self.drones[self.current_master_id].status != DroneStatus.MASTER:
        #         print(f"⚠️ Correcting master status for drone {self.current_master_id}")
        #         self.drones[self.current_master_id].status = DroneStatus.MASTER
        
        # Check for offline drones and update their status
        current_time = time.time()
        for drone in self.drones.values():
            # Skip drones without position data
            if not drone.position:
                continue
                
            # Determine if drone is offline
            is_online = drone.is_online()
            
            # Set appropriate status - offline or current status
            if not is_online and drone.status != DroneStatus.OFFLINE:
                # Only log status changes to reduce console spam
                print(f"⏱️ Drone {drone.drone_id} appears offline (last seen {current_time - drone.last_seen:.1f}s ago)")
                drone.status = DroneStatus.OFFLINE
                
            # Get the appropriate status for this drone
            status = drone.status
            
            # Override status for master drone
            if str(drone.drone_id) == str(self.current_master_id) and is_online:
                status = DroneStatus.MASTER
            
            # Add to plot data
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
        self.ax.set_title('Master-Based 3D Drone Network Visualization')
        
        # Set fixed limits
        self.ax.set_xlim([-5, 5])
        self.ax.set_ylim([-5, 5])
        self.ax.set_zlim([0, 10])
        
        # Initialize scatter plots with placeholder data
        self.scatter_plots = {}
        
        # Add status text at the bottom
        self.info_text = self.fig.text(0.02, 0.02, self.last_status_message, 
                                      fontsize=10, color='black',
                                      bbox=dict(facecolor='white', alpha=0.7))
        
        # Add grid
        self.ax.grid(True, alpha=0.3)
        
        return self.scatter_plots.values()
    
    def _cleanup_very_old_drones(self, cleanup_timeout=60.0):
        """Remove drones that haven't been seen for a very long time"""
        current_time = time.time()
        very_old_drones = [drone_id for drone_id, drone in self.drones.items() 
                      if current_time - drone.last_seen > cleanup_timeout]
        
        for drone_id in very_old_drones:
            print(f"🗑️ Removing very stale drone: {drone_id} (not seen for {cleanup_timeout:.1f}s)")
            del self.drones[drone_id]

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
                
                # Basic label for most drones
                label = f'  {drone_id}'
                
                # Add offline duration for offline drones
                if status == DroneStatus.OFFLINE and drone_id in self.drones:
                    offline_duration = time.time() - (self.drones[drone_id].offline_since or time.time())
                    label = f'  {drone_id} ({int(offline_duration)}s)'
                    
                self.ax.text(x, y, z, label, 
                           fontsize=10, alpha=0.9, weight='bold')        # Add legend if we have any data
        if legend_handles:
            self.ax.legend(handles=legend_handles, loc='upper right', bbox_to_anchor=(1.15, 1))
        
        # Update title with drone count
        online_count = len([d for d in self.drones.values() if d.is_online()])
        offline_count = len([d for d in self.drones.values() if not d.is_online()])
        master_id = self.current_master_id if self.current_master_id else "None"
        
        title = f'Master-Based 3D Drone Network - {online_count} Online'
        if offline_count > 0:
            title += f', {offline_count} Offline'
        title += f' | Master: {master_id}'
        
        self.ax.set_title(title)
        
        # Set fixed limits - no auto-scaling
        self.ax.set_xlim([-5, 5])
        self.ax.set_ylim([-5, 5])
        self.ax.set_zlim([0, 10])
        
        # Update status message
        if self.info_text:
            self.info_text.set_text(self.last_status_message)
            
        # Check how long since last master packet
        time_since_update = time.time() - self.last_master_packet_time
        if time_since_update > 30.0:
            # If no updates for 30 seconds, clear the plot
            self.drones.clear()
            self.last_status_message = "No master updates in 30+ seconds. Waiting for network..."
        
        return scatter_artists
    
    def start_visualization(self, update_interval=1000, master_reset_time=10.0):
        """Start the real-time 3D visualization"""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ Matplotlib not available - cannot start 3D visualization")
            return
        
        self.master_reset_time = master_reset_time  # Store reset time for use in monitoring thread
        
        print("🚁 Starting Master-Based 3D Drone Network Visualization")
        print("👑 Only displaying network state as reported by the current master drone")
        print(f"⚙️ Will reset master search after {master_reset_time}s without updates")
        print("Press Ctrl+C in terminal to exit")
        
        # Start monitoring
        self.start_monitoring()
        
        # Wait a moment for initial data
        time.sleep(2)
        
        # Initialize plot
        artists = self._init_plot()
        
        # Set up animation
        if self.fig:
            self.animation = animation.FuncAnimation(
                self.fig, 
                self._update_plot,
                interval=update_interval,  # Update interval in ms
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
    """Main function for Master-Based 3D drone visualization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Master-Based 3D Drone Network Visualizer")
    parser.add_argument("--update-interval", type=int, default=1000,
                       help="Update interval in milliseconds (default: 1000)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--reset-time", type=int, default=10,
                       help="Time in seconds before resetting master search if current master is silent (default: 10)")
    
    args = parser.parse_args()
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ This visualizer requires matplotlib.")
        print("Install it with: pip install matplotlib")
        return
    
    print("🚁 Initializing Master-Based 3D Drone Network Visualizer...")
    if args.debug:
        print("🔍 Debug mode enabled - will show detailed packet information")
    
    # controller = EnhancedStateController()
    # timeout = controller.master_timeout
    # del controller  # We only needed it for the timeout value
    
    # Create visualizer with debug mode if requested
    visualizer = MasterBasedDroneVisualizer(2.5, debug_mode=args.debug)
    
    try:
        # Start visualization
        print(f"⏱️ Master search reset time: {args.reset_time} seconds")
        print(f"⏱️ Visualization update interval: {args.update_interval}ms")
        visualizer.start_visualization(
            update_interval=args.update_interval,
            master_reset_time=args.reset_time
        )
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