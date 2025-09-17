# 🚁 How to Spawn and Remove Drones

## 📋 Quick Reference

### **Spawning Drones**
```bash
# Method 1: Manual terminal spawning (simplest)
python drone_network_example.py 1001    # Specific ID
python drone_network_example.py         # Random ID

# Method 2: Interactive spawner (recommended)
python drone_spawner.py                 # Interactive mode

# Method 3: Programmatic management
python network_manager.py               # Interactive network manager
```

### **Removing Drones**
- **Ctrl+C** in terminal to stop individual drones
- **Interactive commands** in spawner/manager
- **Programmatic removal** via network manager

---

## 🚀 **Method 1: Manual Terminal Spawning (Simplest)**

### Spawn Drones
Open multiple terminals and run:

```bash
# Terminal 1: First drone
python drone_network_example.py 1001

# Terminal 2: Second drone  
python drone_network_example.py 1002

# Terminal 3: Third drone with visualizer
python drone_visualizer.py --mode realtime --drone-id 1003
```

### Remove Drones
- Press **Ctrl+C** in each terminal to stop that drone
- Close the terminal window

**✅ Pros:** Simple, visual, easy to understand  
**❌ Cons:** Manual, requires multiple terminals

---

## 🎮 **Method 2: Interactive Spawner (Recommended)**

### Start Interactive Spawner
```bash
python drone_spawner.py
```

### Commands Available:
```
🚁 > spawn          # Spawn drone with random ID
🚁 > spawn 1001     # Spawn drone with specific ID  
🚁 > spawn 1002 viz # Spawn drone with visualizer
🚁 > list           # List all active drones
🚁 > remove 1001    # Remove specific drone
🚁 > spawn_multiple 5  # Spawn 5 drones at once
🚁 > remove_all     # Remove all drones
🚁 > quit           # Exit and cleanup
```

### Example Session:
```bash
$ python drone_spawner.py

🚁 DRONE SPAWNER
Commands: spawn, remove, list, spawn_multiple, remove_all, quit

🚁 > spawn 1001
✅ Spawned drone 1001 headless (PID: 12345)

🚁 > spawn 1002 viz  
✅ Spawned drone 1002 with visualizer (PID: 12346)

🚁 > spawn_multiple 3
✅ Spawned drones: [1003, 1004, 1005]

🚁 > list
🚁 Active Drones (5):
   Drone 1001: Running (PID: 12345)
   Drone 1002: Running (PID: 12346)
   Drone 1003: Running (PID: 12347)
   Drone 1004: Running (PID: 12348)
   Drone 1005: Running (PID: 12349)

🚁 > remove 1003
✅ Removed drone 1003

🚁 > remove_all
✅ Removed all 4 drones

🚁 > quit
```

**✅ Pros:** Easy management, clean cleanup, batch operations  
**❌ Cons:** Requires learning commands

---

## 🧠 **Method 3: Programmatic Management**

### Start Network Manager
```bash
python network_manager.py
```

### Interactive Commands:
```
🚁 > add           # Add drone with random ID
🚁 > add 1001      # Add drone with specific ID
🚁 > remove 1001   # Remove specific drone
🚁 > status        # Show network status  
🚁 > visualize     # Start real-time visualizer
🚁 > quit          # Exit and cleanup
```

### Programmatic Demo:
```bash
python network_manager.py demo
```

### Example in Your Code:
```python
from network_manager import NetworkManager

# Create manager
manager = NetworkManager()

# Add drones
manager.add_drone(1001)
manager.add_drone(1002, with_visualizer=True)
manager.add_drone()  # Random ID

# Check status
print(manager.get_network_status())

# Remove specific drone
manager.remove_drone(1001)

# Shutdown all
manager.shutdown()
```

**✅ Pros:** Programmatic control, integration-friendly  
**❌ Cons:** More complex setup

---

## 🎯 **Practical Examples**

### **Quick Test Network**
```bash
# Terminal 1: Start spawner
python drone_spawner.py

# In spawner:
🚁 > spawn_multiple 3
🚁 > spawn 1004 viz  # Add one with visualizer
```

### **Development Workflow**
```bash
# Start with baseline drones
python drone_spawner.py spawn_multiple 2

# Add test drone with visualizer in separate terminal
python drone_visualizer.py --mode realtime --drone-id 9999

# Test your changes, then cleanup
python drone_spawner.py
🚁 > remove_all
```

### **Production Monitoring**
```python
# In your main application
from network_manager import NetworkManager

manager = NetworkManager()

# Start core drones
manager.add_drone(1001)  # Master candidate
manager.add_drone(1002)  # Backup

# Add monitoring drone
manager.add_drone(9999, with_visualizer=True)

# Your application logic...

# Graceful shutdown
manager.shutdown()
```

---

## 🛠️ **Advanced Scenarios**

### **Simulating Drone Failures**
```bash
🚁 > spawn_multiple 5        # Start 5 drones
🚁 > list                    # See all active
🚁 > remove 1002             # Simulate drone 1002 failure
🚁 > remove 1004             # Simulate drone 1004 failure
# Watch network adapt in visualizer
```

### **Dynamic Network Scaling**
```bash
# Start small
🚁 > spawn 1001 viz          # Master with visualizer
🚁 > spawn 1002              # First follower

# Scale up based on demand
🚁 > spawn_multiple 3        # Add 3 more drones

# Scale down
🚁 > remove 1003
🚁 > remove 1004
```

### **Testing ID Conflicts**
```bash
# This will trigger ID conflict resolution
🚁 > spawn 1001
🚁 > spawn 1001              # Same ID - will auto-resolve
```

---

## 🎛️ **Command Summary**

| Method | Spawn Command | Remove Command | Best For |
|--------|---------------|----------------|----------|
| **Manual** | `python drone_network_example.py 1001` | `Ctrl+C` | Learning, testing |
| **Spawner** | `python drone_spawner.py` → `spawn 1001` | `remove 1001` | Operations, testing |
| **Manager** | `python network_manager.py` → `add 1001` | `remove 1001` | Development, integration |

## 🚨 **Important Notes**

1. **Always cleanup**: Use `remove_all` or `Ctrl+C` to properly stop drones
2. **Unique IDs**: Each drone needs a unique ID (auto-generated if not specified)
3. **Network discovery**: New drones automatically discover existing network
4. **Master election**: Lowest ID typically becomes master
5. **Visualizer**: Only one visualizer per network recommended

## ✅ **Best Practices**

- **Start simple**: Use manual spawning for learning
- **Use spawner**: For testing and operations
- **Use manager**: For programmatic integration
- **Always cleanup**: Stop drones properly to avoid orphaned processes
- **Monitor network**: Use visualizer to watch network behavior

Choose the method that best fits your use case! 🚁✨