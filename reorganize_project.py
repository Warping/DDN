#!/usr/bin/env python3
"""
Project Reorganization Script

This script reorganizes the DDN project into a logical folder structure
and updates import statements accordingly.
"""

import os
import shutil
import re
from pathlib import Path

class ProjectReorganizer:
    def __init__(self, project_root="/home/zak/Desktop/DDN"):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup_original"
        
        # Define the new structure
        self.file_mapping = {
            # Core data structures and state management
            "core/": [
                "drone_state.py"
            ],
            
            # Networking and communication
            "networking/": [
                "broadcast_controller.py", 
                "drone_packet.py",
                # Note: comms.py and comm_handler.py already exist in networking/
            ],
            
            # Controllers and state machines
            "controllers/": [
                "state_controller.py",
                "state_controller2.py", 
                "enhanced_state_controller.py"
            ],
            
            # Visualization and monitoring
            "visualization/": [
                "drone_visualizer.py",
                "network_monitor.py"
            ],
            
            # Main applications and runners
            "applications/": [
                "run_drone.py",
                "main.py"
            ],
            
            # Management and utility tools
            "tools/": [
                "drone_spawner.py",
                "network_manager.py", 
                "master_election_demo.py",
                "test_runner.py"
            ],
            
            # Testing scripts
            "tests/": [
                "test_drone_state.py",
                "master_death_test.py",
                "test_passive_visualizer.py"
            ],
            
            # Examples and legacy code
            "examples/": [
                "drone_network_example.py",
                "rns_example.py"
            ]
        }
        
        # Import mapping for updating references
        self.import_mapping = {
            "drone_state": "core.drone_state",
            "broadcast_controller": "networking.broadcast_controller", 
            "drone_packet": "networking.drone_packet",
            "state_controller": "controllers.state_controller",
            "enhanced_state_controller": "controllers.enhanced_state_controller",
            "drone_visualizer": "visualization.drone_visualizer",
            "network_monitor": "visualization.network_monitor"
        }
    
    def create_backup(self):
        """Create backup of original files"""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        self.backup_dir.mkdir()
        
        # Copy all Python files to backup
        for file in self.project_root.glob("*.py"):
            if file.name != "reorganize_project.py":
                shutil.copy2(file, self.backup_dir / file.name)
        
        print(f"✅ Created backup in {self.backup_dir}")
    
    def create_init_files(self):
        """Create __init__.py files to make packages importable"""
        init_content = '"""Package initialization"""'
        
        folders = ["core", "networking", "controllers", "visualization", "applications", "tools", "tests", "examples"]
        
        for folder in folders:
            folder_path = self.project_root / folder
            if folder_path.exists():
                init_file = folder_path / "__init__.py"
                with open(init_file, 'w') as f:
                    f.write(init_content)
                print(f"📝 Created {init_file}")
    
    def move_files(self):
        """Move files to their new locations"""
        moved_files = []
        
        for target_dir, files in self.file_mapping.items():
            target_path = self.project_root / target_dir
            
            for filename in files:
                source_file = self.project_root / filename
                target_file = target_path / filename
                
                if source_file.exists():
                    shutil.move(str(source_file), str(target_file))
                    moved_files.append((filename, target_dir))
                    print(f"📁 Moved {filename} → {target_dir}")
                else:
                    print(f"⚠️  {filename} not found, skipping")
        
        return moved_files
    
    def update_imports_in_file(self, file_path):
        """Update import statements in a single file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Update import statements
            for old_import, new_import in self.import_mapping.items():
                # Handle different import patterns
                patterns = [
                    (f"from {old_import} import", f"from {new_import} import"),
                    (f"import {old_import}", f"import {new_import}"),
                    (f"from {old_import}\\.", f"from {new_import}."),
                ]
                
                for old_pattern, new_pattern in patterns:
                    content = re.sub(old_pattern, new_pattern, content)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                return True
            
        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
            return False
        
        return False
    
    def update_all_imports(self):
        """Update import statements in all Python files"""
        updated_files = []
        
        # Update imports in all Python files
        for py_file in self.project_root.rglob("*.py"):
            if py_file.name != "reorganize_project.py":
                if self.update_imports_in_file(py_file):
                    updated_files.append(str(py_file.relative_to(self.project_root)))
        
        if updated_files:
            print(f"\n🔄 Updated imports in {len(updated_files)} files:")
            for file in updated_files:
                print(f"   📝 {file}")
        else:
            print("ℹ️  No import updates needed")
    
    def create_project_structure_doc(self):
        """Create documentation of the new project structure"""
        doc_content = '''# DDN Project Structure

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
'''
        
        doc_file = self.project_root / "PROJECT_STRUCTURE.md"
        with open(doc_file, 'w') as f:
            f.write(doc_content)
        
        print(f"📖 Created project structure documentation: {doc_file}")
    
    def reorganize(self):
        """Perform the complete reorganization"""
        print("🚁 DDN PROJECT REORGANIZATION")
        print("=" * 50)
        
        # Step 1: Create backup
        print("\n📦 Step 1: Creating backup...")
        self.create_backup()
        
        # Step 2: Move files to new structure
        print("\n📁 Step 2: Moving files to new structure...")
        moved_files = self.move_files()
        
        # Step 3: Create __init__.py files
        print("\n📝 Step 3: Creating package initialization files...")
        self.create_init_files()
        
        # Step 4: Update import statements
        print("\n🔄 Step 4: Updating import statements...")
        self.update_all_imports()
        
        # Step 5: Create documentation
        print("\n📖 Step 5: Creating project documentation...")
        self.create_project_structure_doc()
        
        print(f"\n✅ Reorganization complete!")
        print(f"📦 Original files backed up to: {self.backup_dir}")
        print(f"📖 See PROJECT_STRUCTURE.md for usage information")
        
        return moved_files

def main():
    reorganizer = ProjectReorganizer()
    
    print("This will reorganize your DDN project into a structured folder layout.")
    print("A backup will be created before making any changes.")
    
    response = input("\nProceed with reorganization? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        try:
            moved_files = reorganizer.reorganize()
            
            print(f"\n🎉 Project successfully reorganized!")
            print(f"📊 Moved {len(moved_files)} files into organized folders")
            
        except Exception as e:
            print(f"\n❌ Error during reorganization: {e}")
            print("Check the backup folder if you need to restore files")
    else:
        print("❌ Reorganization cancelled")

if __name__ == "__main__":
    main()