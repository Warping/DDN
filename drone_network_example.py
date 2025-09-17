#!/usr/bin/env python3
"""
Drone Network Management Example

This script demonstrates how to use the enhanced drone state management system.
Each drone will:
1. Start with a random ID
2. Discover other drones in the network
3. Resolve ID conflicts if they occur
4. Establish a network hierarchy with master/slave roles
5. Maintain network awareness through heartbeats

Usage:
    python drone_network_example.py [drone_id]

If no drone_id is provided, a random one will be generated.
"""

import sys
import time
import signal
from enhanced_state_controller import EnhancedStateController

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down drone network controller...")
    sys.exit(0)

def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get drone ID from command line argument if provided
    drone_id = None
    if len(sys.argv) > 1:
        try:
            drone_id = int(sys.argv[1])
            if drone_id < 1 or drone_id > 65535:
                print("Drone ID must be between 1 and 65535")
                sys.exit(1)
        except ValueError:
            print("Invalid drone ID. Please provide a number between 1 and 65535")
            sys.exit(1)
    
    print("=" * 50)
    print("Drone Network Management System")
    print("=" * 50)
    
    if drone_id:
        print(f"Starting drone with ID: {drone_id}")
    else:
        print("Starting drone with random ID...")
    
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Create and start the enhanced state controller
        controller = EnhancedStateController(drone_id)
        
        # Display initial status
        print(f"Drone initialized with ID: {controller.drone_network.get_self_id()}")
        print("Starting network discovery...")
        
        # Start the control loop
        controller.control_loop()
        
    except KeyboardInterrupt:
        print("\nReceived shutdown signal")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        print("Drone network controller stopped")

if __name__ == "__main__":
    main()