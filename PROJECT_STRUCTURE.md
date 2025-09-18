# DDN Project Structure

## 📁 Folder Organization

### `core/`
**Foundation classes and data structures**
- `drone_state.py` - Core DroneState and DroneNetwork classes

### `networking/`
**Communication and networking components**
- `broadcast_controller.py` - RNS broadcast handling
- `drone_packet.py` - Message protocol definitions
- `comms.py` - Basic communication interface
- `comm_handler.py` - Communication handler

### `controllers/`
**State management and control logic**
- `enhanced_state_controller.py` - Main controller with master election
- `state_controller.py` - Basic state controller
- `state_controller2.py` - Alternative state controller

### `visualization/`
**Monitoring and visualization tools**
- `drone_visualizer.py` - Network visualization dashboard
- `network_monitor.py` - Real-time network monitoring

### `applications/`
**Main runnable applications**
- `run_drone.py` - Primary drone application
- `main.py` - Legacy main application

### `tools/`
**Management and utility tools**
- `drone_spawner.py` - Process management for drones
- `network_manager.py` - Programmatic network management
- `master_election_demo.py` - Master election demonstration
- `test_runner.py` - Interactive test runner

### `tests/`
**Testing and validation scripts**
- `test_drone_state.py` - Unit tests for core classes
- `master_death_test.py` - Master failure testing
- `test_passive_visualizer.py` - Visualizer testing

### `examples/`
**Example code and legacy files**
- `drone_network_example.py` - Example implementations
- `rns_example.py` - RNS networking examples

## 🚀 Usage After Reorganization

### Running Applications
```bash
# Run a single drone
python -m applications.run_drone 1001

# Start network monitor
python -m visualization.network_monitor

# Launch drone spawner
python -m tools.drone_spawner
```

### Development
```bash
# Run tests
python -m tests.test_drone_state

# Demo master election
python -m tools.master_election_demo
```

### Imports in Code
```python
# Core classes
from core.drone_state import DroneState, DroneNetwork

# Controllers
from controllers.enhanced_state_controller import EnhancedStateController

# Networking
from networking.broadcast_controller import BroadcastHandler
from networking.drone_packet import DronePacket

# Visualization
from visualization.drone_visualizer import DroneNetworkVisualizer
```
