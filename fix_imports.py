#!/usr/bin/env python3
"""
Quick fix for import paths after reorganization
"""

import os
import sys
from pathlib import Path

def fix_imports_in_file(file_path):
    """Add project root to sys.path in files that need it"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if file imports from reorganized modules
        needs_fix = any(module in content for module in [
            'from core.', 'from networking.', 'from controllers.', 
            'from visualization.', 'from applications.', 'from tools.'
        ])
        
        if not needs_fix:
            return False
        
        # Check if already has sys.path fix
        if 'project_root' in content and 'sys.path.insert' in content:
            return False
        
        # Find the import section
        lines = content.split('\n')
        import_start = None
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_start = i
                break
        
        if import_start is None:
            return False
        
        # Insert sys.path fix before first import
        sys_path_fix = [
            "",
            "# Add project root to Python path for imports",
            "import os",
            "import sys",
            "project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
            "if project_root not in sys.path:",
            "    sys.path.insert(0, project_root)",
            ""
        ]
        
        # Insert the fix
        new_lines = lines[:import_start] + sys_path_fix + lines[import_start:]
        new_content = '\n'.join(new_lines)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    project_root = Path("/home/zak/Desktop/DDN")
    
    # Files that need fixing (exclude documentation and the fix script itself)
    files_to_fix = [
        "applications/run_drone.py",
        "tools/network_manager.py", 
        "examples/drone_network_example.py",
        "visualization/network_monitor.py"
    ]
    
    print("🔧 Fixing import paths after reorganization...")
    
    fixed_count = 0
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            if fix_imports_in_file(full_path):
                print(f"✅ Fixed imports in {file_path}")
                fixed_count += 1
            else:
                print(f"ℹ️  {file_path} - no fix needed")
        else:
            print(f"⚠️  {file_path} not found")
    
    print(f"\n🎉 Fixed imports in {fixed_count} files")
    print("\nNow you can run:")
    print("  python visualization/drone_visualizer.py")
    print("  python applications/run_drone.py 1001")
    print("  python tools/network_manager.py")

if __name__ == "__main__":
    main()