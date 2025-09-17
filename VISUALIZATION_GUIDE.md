# 🚁 Drone Visualizer - Single Tool Guide

## Overview
`drone_visualizer.py` is your **single comprehensive visualization tool** for the drone network.

## 🚀 Usage Modes

### 1. Real-time Dashboard (Main Mode)
```bash
python drone_visualizer.py --mode realtime --drone-id 1001
```
**Features:**
- 📊 Live network overview
- 📋 Detailed drone table (ID, status, position, battery, reliability)
- 🌐 Network topology with master/slave hierarchy
- 📈 Network statistics and performance metrics
- ⏱️ Auto-refreshing display

### 2. Data Export
```bash
python drone_visualizer.py --mode export --drone-id 1001
```
**Output:** JSON file with complete network state for analysis/logging

### 3. 3D Position Plot
```bash
python drone_visualizer.py --mode plot --drone-id 1001
```
**Requires:** `pip install matplotlib`
**Shows:** 3D scatter plot of drone positions with status colors

## 🔧 Integration Examples

### Embedded in Your Control Loop
```python
from drone_visualizer import SimpleDroneMonitor
from enhanced_state_controller import EnhancedStateController

# Create controller and monitor
controller = EnhancedStateController(1001)
monitor = SimpleDroneMonitor(controller)

# In your main loop:
while True:
    controller.process_incoming_packets()
    # ... your drone logic ...
    
    # Simple one-line status update
    monitor.display_compact_status()
    # Output: 🚁 Network: 3/4 online | Drones: 1001👑*, 1002🔵, 1003🟢
```

### Full Visualization Dashboard
```python
from drone_visualizer import DroneNetworkVisualizer
from enhanced_state_controller import EnhancedStateController

controller = EnhancedStateController(1001)
visualizer = DroneNetworkVisualizer(controller)

# Start real-time dashboard
visualizer.real_time_display()
```

## 📊 What You'll See

### Drone Status Symbols
- 👑 **Master** - Network coordinator
- 🔵 **Slave** - Following master  
- 🟢 **Connected** - In network
- 🔍 **Seeking** - Looking for network
- ⚫ **Offline** - Disconnected
- ❌ **Lost** - Connection lost

### Self Identification
- 🔸 **Your drone** - Highlighted with special marker
- 🔹 **Other drones** - Standard marker
- → **Table marker** - Points to your drone in tables

### Network Topology Example
```
📡 Network Topology:
   👑 Master: 🔸 Drone 1001
   ├── Slave: 🔹 Drone 1002  
   └── Slave: 🔹 Drone 1003
   🔗 Connected:
      • 🔹 Drone 1004
```

## ⚙️ Command Options

```bash
# Basic usage
python drone_visualizer.py

# Specify drone ID  
python drone_visualizer.py --drone-id 1001

# Different modes
python drone_visualizer.py --mode realtime    # Default
python drone_visualizer.py --mode export
python drone_visualizer.py --mode plot

# Custom export filename
python drone_visualizer.py --mode export --export-file my_network.json

# Adjust update rate
python drone_visualizer.py --mode realtime --update-interval 0.5
```

## 🎯 Quick Testing

```bash
# Terminal 1: Start first drone with visualization
python drone_visualizer.py --drone-id 1001

# Terminal 2: Start second drone  
python drone_network_example.py 1002

# Terminal 3: Start third drone
python drone_network_example.py 1003
```

Watch the visualization show:
1. Network discovery
2. Master election (lowest ID wins)
3. Hierarchy establishment
4. Real-time status updates

## 📁 File Organization

**Keep only these files:**
- ✅ `drone_visualizer.py` - **Single visualization tool**
- ✅ `enhanced_state_controller.py` - Main controller
- ✅ `drone_state.py` - State management
- ✅ `drone_packet.py` - Communication protocol
- ✅ Other core files...

**Removed (cleaned up):**
- ❌ `visualize_drones.py` - Redundant
- ❌ `simple_drone_with_viz.py` - Redundant  
- ❌ `test_visualization_fix.py` - No longer needed

This gives you **one powerful tool** instead of multiple scattered visualization scripts! 🎉