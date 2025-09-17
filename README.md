# Drone Distributed Network (DDN) - State Management System

A comprehensive drone network state management system that enables drones to discover each other, manage network topology, and coordinate operations in a distributed environment.

## Features

### 🚁 Drone State Management
- **Unique ID Generation**: Each drone starts with a random unique ID (1-65535)
- **ID Conflict Resolution**: Automatic detection and resolution of ID conflicts
- **Position Tracking**: 3D position coordinates for each drone
- **Battery Monitoring**: Real-time battery level tracking
- **Connection Status**: Online/offline status with last-seen timestamps
- **Reliability Scoring**: Ping/response ratio tracking for network reliability

### 🌐 Network Discovery
- **Automatic Discovery**: Drones automatically discover each other on the network
- **Heartbeat System**: Periodic heartbeats maintain network presence
- **Network Topology**: Real-time view of all connected drones
- **Master Election**: Automatic election of master drone for coordination
- **Status Synchronization**: Periodic sharing of network status between drones

### 📡 Communication Protocol
- **Multiple Packet Types**: Support for discovery, heartbeat, status, and control messages
- **Broadcast Communication**: Uses Reticulum Network Stack for mesh networking
- **Acknowledgment System**: Reliable message delivery with ACK responses
- **Conflict Resolution**: Automatic handling of network conflicts

## Architecture

### Core Components

1. **DroneState**: Individual drone state management
2. **DroneNetwork**: Network-wide state coordination
3. **DronePacket**: Communication protocol implementation
4. **EnhancedStateController**: Main control logic and event handling
5. **BroadcastHandler**: Network communication interface

### State Machine

```
SEEKING → CONNECTED → MASTER/SLAVE
    ↑         ↓
    ←─────────
```

- **SEEKING**: Initial state, looking for other drones
- **CONNECTED**: Found other drones, establishing connections
- **MASTER**: Elected as network coordinator
- **SLAVE**: Following master drone's coordination

## Quick Start

### Basic Usage

```python
from enhanced_state_controller import EnhancedStateController

# Create controller with random ID
controller = EnhancedStateController()

# Or with specific ID
controller = EnhancedStateController(drone_id=1001)

# Start the control loop
controller.control_loop()
```

### Visualization

```bash
# Real-time network visualization dashboard
python drone_visualizer.py --mode realtime --drone-id 1001

# Export network data to JSON
python drone_visualizer.py --mode export --drone-id 1001

# 3D plot (requires matplotlib)
python drone_visualizer.py --mode plot --drone-id 1001
```

### Running the Example

```bash
# Start with random ID
python drone_network_example.py

# Start with specific ID
python drone_network_example.py 1001
```

### Testing the System

```bash
# Run unit tests
python test_drone_state.py

# Run interactive demo
python test_drone_state.py --interactive
```

## Network Protocol

### Packet Types

| Type | Purpose | Parameters |
|------|---------|------------|
| `DISCOVERY_ANNOUNCE` | Announce presence to network | position, battery_level, capabilities |
| `DISCOVERY_RESPONSE` | Respond to discovery | position, battery_level, capabilities |
| `HEARTBEAT` | Maintain network presence | position, battery_level |
| `NETWORK_STATUS` | Share topology information | known_drones, master_id |
| `PING` | Test connectivity | - |
| `ACK` | Acknowledge messages | response_data |
| `ID_CONFLICT_RESOLUTION` | Resolve ID conflicts | old_id, new_id |
| `ELECT_MASTER` | Master election process | candidate_id, criteria |

### Message Format

```json
{
    "timestamp": 1234567890.123,
    "drone_id": 1001,
    "destination_id": 1002,
    "current_state": "CONNECTED",
    "action": "HEARTBEAT",
    "params": {
        "position": [10.5, 20.3, 5.0],
        "battery_level": 85.5,
        "heartbeat_time": 1234567890.123
    }
}
```

## Visualization

The `drone_visualizer.py` provides comprehensive network visualization:

### Real-time Dashboard
```bash
python drone_visualizer.py --mode realtime --drone-id 1001
```
Shows live network status with:
- 📋 **Drone Table**: ID, status, position, battery, reliability  
- 🌐 **Network Topology**: Master/slave hierarchy
- 📈 **Statistics**: Network health and performance metrics
- 🎯 **Real-time Updates**: Auto-refreshing display

### Data Export
```bash
python drone_visualizer.py --mode export --drone-id 1001 --export-file my_network.json
```
Exports network state to JSON for analysis or logging.

### 3D Position Plot
```bash
python drone_visualizer.py --mode plot --drone-id 1001
```
Creates 3D matplotlib visualization of drone positions (requires `matplotlib`).

### Embedded Monitoring
```python
from drone_visualizer import SimpleDroneMonitor

controller = EnhancedStateController()
monitor = SimpleDroneMonitor(controller)

# In your control loop:
monitor.display_compact_status()  # Shows: 🚁 Network: 3/4 online | Drones: 1001👑*, 1002🔵
```

## Advanced Features

### ID Conflict Resolution

When two drones start with the same random ID:

1. Conflict is detected through network announcements
2. The conflicting drone generates a new random ID
3. Resolution is announced to the network
4. All drones update their network maps

### Master Election

Master election uses a simple algorithm (lowest ID wins), but can be extended:

```python
def elect_master(self) -> Optional[int]:
    online_drones = self.get_online_drones()
    if not online_drones:
        return None
    
    # Custom election criteria
    master_candidate = max(online_drones, key=lambda d: d.battery_level)
    # or min(online_drones, key=lambda d: d.drone_id)
    # or based on capabilities, signal strength, etc.
    
    return master_candidate.drone_id
```

### Network Cleanup

Offline drones are automatically removed from the network:

```python
# Cleanup drones offline for more than 60 seconds
network.cleanup_offline_drones(timeout=60.0)
```

## Configuration

### Timing Parameters

```python
controller = EnhancedStateController()

# Adjust timing intervals
controller.discovery_interval = 5.0    # Discovery announcements
controller.heartbeat_interval = 10.0   # Heartbeat messages
controller.network_sync_interval = 15.0 # Status synchronization
```

### Network Settings

```python
# Maximum discovery attempts before giving up
controller.max_discovery_attempts = 10

# Minimum time before network is considered stable
controller.min_stable_time = 30.0
```

## Compatibility

The system maintains backward compatibility with existing code through the `StateController` wrapper class:

```python
# Legacy interface still works
from enhanced_state_controller import StateController

controller = StateController()
controller.switch_states("CONNECTED")
print(f"Current state: {controller.current_state}")
print(f"Drone ID: {controller.drone_id}")
print(f"Detected drones: {controller.detected_drones}")
```

## Dependencies

- Python 3.7+
- Reticulum Network Stack (RNS)
- Standard library modules: `json`, `time`, `random`, `enum`, `typing`

## File Structure

```
DDN/
├── drone_state.py                 # Core state management classes
├── enhanced_state_controller.py   # Main controller logic
├── drone_packet.py               # Communication protocol
├── broadcast_controller.py       # Network interface
├── drone_visualizer.py           # Network visualization tool
├── drone_network_example.py      # Usage example
├── test_drone_state.py          # Test suite
└── README.md                    # This file
```

## Contributing

When extending the system:

1. **Add new packet types** in `DronePacket` class
2. **Extend state management** in `DroneState` and `DroneNetwork` classes
3. **Update control logic** in `EnhancedStateController`
4. **Add tests** in `test_drone_state.py`
5. **Update documentation** in this README

## Troubleshooting

### Common Issues

1. **ID Conflicts**: The system automatically resolves these, but check logs for resolution messages
2. **Network Isolation**: Ensure all drones are on the same Reticulum network
3. **Timing Issues**: Adjust interval parameters if network is too slow/fast
4. **Memory Usage**: Cleanup intervals can be adjusted for memory-constrained devices

### Debug Mode

Enable verbose logging by modifying the print statements in the controller or adding a debug flag:

```python
controller = EnhancedStateController()
controller.debug = True  # Add this feature if needed
```

## License

This project is part of the Drone Distributed Network (DDN) system.