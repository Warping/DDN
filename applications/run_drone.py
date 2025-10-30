#!/usr/bin/env python3
"""
Simple drone runner for testing
"""


# Add project root to Python path for imports
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sys
import time
from controllers.enhanced_state_controller import EnhancedStateController
from core.drone_state import DroneStatus
from controllers.movement_state_controller import MovementStateController

from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np
import threading


def main(visualize=False):
    
    # Don't initialize visualization at start - wait until we become master
    global visualization_initialized, was_master_last_frame
    
    drone_id = None
    quiet_mode = True  # Default to quiet for testing
    
    # Parse command line arguments (skip visualization flags)
    args = [arg for arg in sys.argv[1:] if arg not in ["--visualize", "-v"]]
    
    if len(args) > 0:
        try:
            drone_id = int(args[0])
        except ValueError:
            print(f"Invalid drone ID: {args[0]}")
            sys.exit(1)
    
    # Check for quiet flag
    if len(args) > 1 and args[1] == "--verbose":
        quiet_mode = False
    
    print(f"🚁 Starting drone {drone_id if drone_id else 'with random ID'}...")
    
    try:
        # Create enhanced state controller
        controller = EnhancedStateController(drone_id, quiet_mode=quiet_mode)
        
        print(f"✅ Drone {controller.drone_network.get_self_id()} is running")
        if visualize:
            print("📊 Visualization will be enabled when this drone becomes master")
        print("Press Ctrl+C to stop")
        
        # Main control loop
        while True:
            old_network_state = controller.query_network_state()
            current_time = time.time()
            
            # Process incoming packets
            controller.process_incoming_packets()
            
            # Discovery logic
            if (controller.drone_network.self_drone.status == DroneStatus.SEEKING and
                current_time - controller.last_discovery_time > controller.discovery_interval and
                controller.discovery_attempts < controller.max_discovery_attempts):
                
                controller.send_discovery_announcement()
                controller.last_discovery_time = current_time
            
            # Heartbeat logic
            if (controller.drone_network.self_drone.status in [DroneStatus.CONNECTED, 
                                                               DroneStatus.MASTER, 
                                                               DroneStatus.SLAVE] and
                current_time - controller.last_heartbeat_time > controller.heartbeat_interval):
                
                controller.send_heartbeat()
                # controller.print_network_state()
                controller.last_heartbeat_time = current_time
            
            # Network status sharing (especially important for masters)
            if (controller.drone_network.self_drone.status == DroneStatus.MASTER and
                current_time - controller.last_network_sync_time > controller.network_sync_interval):
                
                network_state = controller.query_network_state()
                # Use a movement controller to simulate position updates
                movement_controller = MovementStateController(network_state, old_network_state)
                # Check if network state has any connected drones or seeking drones before updating positions
                currently_connecting = network_state['drones_by_role']['connected'] + network_state['drones_by_role']['seeking']
                if not currently_connecting:
                    new_positions = movement_controller.update_slave_positions()
                    if new_positions:
                        print(f"Update slave positions: {new_positions}")
                        controller.update_slave_positions(new_positions)
                else:
                    print("No position updates needed")
                
                controller.share_network_status()
                
                controller.last_network_sync_time = current_time
            
            # Update state (includes master election logic)
            controller.update_state_based_on_network()
            
            # Check if visualization should be shown (only for masters)
            is_master = controller.drone_network.self_drone.status == DroneStatus.MASTER
            
            if visualize:
                # Initialize visualization when becoming master
                if is_master and not visualization_initialized:
                    print("👑 Became master - initializing visualization")
                    init_visualization()
                    visualization_initialized = True
                    was_master_last_frame = True
                
                # Close visualization when no longer master
                elif not is_master and visualization_initialized and was_master_last_frame:
                    print("📉 No longer master - closing visualization")
                    close_visualization()
                    visualization_initialized = False
                    was_master_last_frame = False
                
                # Update visualization if we are master
                if is_master and visualization_initialized:
                    current_network_state = controller.query_network_state()
                    run_visualization(current_network_state)
                    was_master_last_frame = True
                elif not is_master:
                    was_master_last_frame = False
                    
            time.sleep(0.001)  # Small delay to prevent high CPU usage
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping drone {controller.drone_network.get_self_id()}")
        if visualization_initialized:
            close_visualization()
    except Exception as e:
        print(f"❌ Error: {e}")
        stacktrace = sys.exc_info()[2]
        import traceback
        traceback.print_tb(stacktrace)
    finally:
        if visualization_initialized:
            close_visualization()
        sys.exit(1)
        
# Global variables for visualization
fig = None
ax = None
visualization_lock = threading.Lock()
visualization_initialized = False
was_master_last_frame = False

def init_visualization():
    """Set up 3D visualization using matplotlib"""
    global fig, ax
    
    # Enable interactive mode
    plt.ion()
    
    # Create figure and 3D axis (don't raise window on creation)
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # Configure matplotlib to not steal focus
    # Get the figure manager and configure window behavior
    try:
        manager = plt.get_current_fig_manager()
        if hasattr(manager, 'window'):
            # For different backends, prevent window from stealing focus
            try:
                # Try to set window to not raise on updates
                manager.window.attributes('-topmost', 0)  # Tkinter backend
            except:
                pass
    except:
        pass
    
    # Set up the plot appearance
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_zlabel('Z Position (m)')
    ax.set_title('Drone Network - 3D Visualization')
    
    # Set axis limits (adjust based on your coordinate system)
    ax.set_xlim([-10, 10])
    ax.set_ylim([-10, 10])
    ax.set_zlim([0, 10])
    
    # Set background color (try-except for compatibility)
    try:
        ax.xaxis.pane.fill = False # type: ignore
        ax.yaxis.pane.fill = False # type: ignore
        ax.zaxis.pane.fill = False # type: ignore
        
        # Make pane edges transparent
        ax.xaxis.pane.set_edgecolor('w') # type: ignore
        ax.yaxis.pane.set_edgecolor('w') # type: ignore
        ax.zaxis.pane.set_edgecolor('w') # type: ignore
    except AttributeError:
        # Older matplotlib versions might not have pane attributes
        pass
    
    # Set grid
    ax.grid(True, alpha=0.3)
    
    print("🎨 3D Visualization initialized")

def close_visualization():
    """Close and cleanup the visualization window"""
    global fig, ax, visualization_initialized
    
    try:
        if fig is not None:
            plt.close(fig)
            fig = None
            ax = None
            visualization_initialized = False
            print("🎨 Visualization closed")
    except Exception as e:
        print(f"⚠️ Error closing visualization: {e}")

def run_visualization(network_state=None):
    """Update the 3D visualization with current drone positions and online status of each drone"""
    global fig, ax
    
    if fig is None or ax is None:
        print("⚠️ Visualization not initialized. Call init_visualization() first.")
        return
    
    # If no network state provided, we can't visualize
    if network_state is None:
        return
    
    # Use thread lock to prevent concurrent updates
    with visualization_lock:
        try:
            # Clear the current plot
            ax.clear()
            
            # Reset plot settings after clearing
            ax.set_xlabel('X Position (m)')
            ax.set_ylabel('Y Position (m)')
            ax.set_zlabel('Z Position (m)')
            ax.set_title(f'Drone Network - 3D Visualization (Viewed by Drone {network_state["queried_by"]})')
            ax.set_xlim([-10, 10])
            ax.set_ylim([-10, 10])
            ax.set_zlim([0, 10])
            ax.grid(True, alpha=0.3)
            
            # Define colors for different drone statuses
            status_colors = {
                'master': 'red',
                'slave': 'blue', 
                'connected': 'green',
                'seeking': 'orange',
                'offline': 'gray'
            }
            
            # Define markers for different drone types
            status_markers = {
                'master': '^',  # Triangle up
                'slave': 'o',   # Circle
                'connected': 's',  # Square
                'seeking': 'D',    # Diamond
                'offline': 'x'     # X mark
            }
            
            # Track master position for connection lines
            master_positions = []
            
            # Plot drones by role
            roles = network_state['drones_by_role']
            all_drones = network_state['drones_by_role']['masters'] + \
                         network_state['drones_by_role']['slaves'] + \
                         network_state['drones_by_role']['connected'] + \
                         network_state['drones_by_role']['seeking']
            for drone in roles['masters'] + roles['slaves'] + roles['connected']:
                x, y, z = drone['position']
                drone_id = drone['drone_id']
                status = drone['status']
                is_online = drone['is_online']
                is_self = drone['is_self']
                battery = drone['battery_level']
                
                # Determine color and marker
                color = status_colors.get(status, 'black')
                marker = status_markers.get(status, 'o')
                
                # If drone is offline, use gray color
                if not is_online:
                    color = 'gray'
                    marker = 'x'
                
                # Size based on battery level (larger = more battery)
                size = 50 + (battery / 100.0) * 100  # Size range: 50-150
                
                # Special highlighting for self drone
                if is_self:
                    # Add a golden ring around self drone
                    ax.scatter(x, y, z, s=size+50, c='gold', marker='o', 
                            alpha=0.3, edgecolors='gold', linewidths=2)
                
                # Plot the drone
                scatter = ax.scatter(x, y, z, s=size, c=color, marker=marker, 
                                alpha=0.8, edgecolors='black', linewidths=0.5)
                
                # Add drone ID label
                ax.text(x, y, z + 0.3, f'D{drone_id}', fontsize=8, 
                    weight='bold' if is_self else 'normal')
                
                # Add battery level as small text
                ax.text(x, y, z - 0.3, f'{battery:.0f}%', fontsize=6, alpha=0.7)
                
                # Store master positions for connection lines
                if status == 'master' and is_online:
                    master_positions.append((x, y, z, drone_id))
            
            
            
            
            # Draw connection lines from masters to slaves
            if master_positions:
                masters = network_state['drones_by_role']['masters']
                first_master = masters[0] if masters else None
                slaves = network_state['drones_by_role']['slaves']
                for drone in slaves:
                    # if drone['status'] == 'slave' and drone['is_online']:
                    slave_x, slave_y, slave_z = drone['position']
                        
                        # Connect to nearest master (or just the first one for simplicity)
                    for master_x, master_y, master_z, master_id in master_positions:
                        ax.plot([master_x, slave_x], [master_y, slave_y], [master_z, slave_z], 
                                'k--', alpha=0.3, linewidth=1)
            
            # Add legend
            legend_elements = []
            for status, color in status_colors.items():
                if status in [drone['status'] for drone in all_drones]:
                    marker = status_markers[status]
                    legend_elements.append(Line2D([0], [0], marker=marker, color='w', 
                                                     markerfacecolor=color, markersize=8, 
                                                     label=status.capitalize()))
            
            if legend_elements:
                ax.legend(handles=legend_elements, loc='upper right')
            
            # Add network statistics as text
            stats = network_state['network_stats']
            stats_text = f"Total: {stats['total_drones']} | Online: {stats['online_drones']} | Masters: {stats['master_count']} | Slaves: {stats['slave_count']}"
            fig.suptitle(stats_text, fontsize=10, y=0.95)
            
            # Add timestamp
            ax.text2D(0.02, 0.98, f"Updated: {network_state['query_time']}", 
                     transform=ax.transAxes, fontsize=8, verticalalignment='top')
            
            # Force update without stealing focus
            # Use flush_events instead of pause to avoid window focus issues
            fig.canvas.draw_idle()  # Request a draw without forcing immediate update
            fig.canvas.flush_events()  # Process pending GUI events without blocking
            
        except Exception as e:
            print(f"❌ Visualization error: {e}")
            import traceback
            traceback.print_exc()
    

if __name__ == "__main__":
    # Check for visualization flag
    visualize = "--visualize" in sys.argv or "-v" in sys.argv
    main(visualize=visualize)