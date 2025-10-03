#!/usr/bin/env python3
"""
Network Query Tool

This tool allows you to query the state of the drone network from any drone.
It provides comprehensive information about masters, slaves, positions, and timing.
"""

import os
import sys
import time
import json

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from controllers.enhanced_state_controller import EnhancedStateController

def main():
    print("🔍 Network State Query Tool")
    print("=" * 50)
    
    # Parse command line arguments
    drone_id = None
    export_json = False
    continuous = False
    interval = 5.0
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--drone-id" and i + 1 < len(sys.argv):
            try:
                drone_id = int(sys.argv[i + 1])
                i += 1
            except ValueError:
                print(f"❌ Invalid drone ID: {sys.argv[i + 1]}")
                sys.exit(1)
        elif arg == "--export-json":
            export_json = True
        elif arg == "--continuous":
            continuous = True
        elif arg == "--interval" and i + 1 < len(sys.argv):
            try:
                interval = float(sys.argv[i + 1])
                i += 1
            except ValueError:
                print(f"❌ Invalid interval: {sys.argv[i + 1]}")
                sys.exit(1)
        elif arg == "--help":
            print_help()
            sys.exit(0)
        else:
            print(f"❌ Unknown argument: {arg}")
            print("Use --help for usage information")
            sys.exit(1)
        i += 1
    
    print(f"🚁 Connecting to drone network...")
    if drone_id:
        print(f"   Using drone ID: {drone_id}")
    else:
        print("   Using random drone ID")
    
    try:
        # Create a drone controller for network access
        controller = EnhancedStateController(drone_id, quiet_mode=True)
        
        # Give it a moment to discover the network
        print("⏳ Discovering network state...")
        time.sleep(2)
        
        if continuous:
            print(f"🔄 Continuous monitoring every {interval} seconds (Ctrl+C to stop)")
            try:
                while True:
                    print(f"\n{'='*20} {time.strftime('%H:%M:%S')} {'='*20}")
                    controller.print_network_state()
                    
                    if export_json:
                        controller.export_network_state_json()
                    
                    time.sleep(interval)
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
        else:
            # Single query
            controller.print_network_state()
            
            if export_json:
                filename = controller.export_network_state_json()
                if filename:
                    print(f"\n💾 Network state saved to: {filename}")
        
        # Get raw data for programmatic access
        state = controller.query_network_state()
        
        print(f"\n📋 QUICK SUMMARY:")
        print(f"   Query Time: {state['query_time']}")
        print(f"   Master: {state['network_stats']['current_master_id'] or 'None'}")
        print(f"   Online Drones: {state['network_stats']['online_drones']}")
        print(f"   Total Known: {state['network_stats']['total_drones']}")
        
        return state
        
    except KeyboardInterrupt:
        print("\n🛑 Query interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def print_help():
    print("""
🔍 Network Query Tool Usage:

python tools/network_query.py [OPTIONS]

OPTIONS:
    --drone-id ID       Use specific drone ID for querying (default: random)
    --export-json       Export network state to JSON file
    --continuous        Continuous monitoring mode
    --interval SECONDS  Update interval for continuous mode (default: 5.0)
    --help             Show this help message

EXAMPLES:
    # Single network query
    python tools/network_query.py
    
    # Query from specific drone
    python tools/network_query.py --drone-id 1001
    
    # Export to JSON file
    python tools/network_query.py --export-json
    
    # Continuous monitoring
    python tools/network_query.py --continuous --interval 3.0
    
    # Full featured monitoring
    python tools/network_query.py --drone-id 2000 --continuous --export-json

NETWORK STATE INFORMATION:
    • Master and slave identification
    • Drone positions (x, y, z coordinates)
    • Battery levels and signal strength
    • Online/offline status with timestamps
    • Network topology and election status
    """)

if __name__ == "__main__":
    main()