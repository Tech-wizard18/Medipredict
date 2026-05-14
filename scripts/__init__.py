# scripts/__init__.py
"""
MediPredict Scripts Package
Provides utility scripts for system management
"""

import os
import sys
from pathlib import Path

# Get scripts directory
SCRIPTS_DIR = Path(__file__).parent

def list_scripts():
    """List all available scripts"""
    scripts = []
    for file in SCRIPTS_DIR.glob("*.py"):
        if file.name != "__init__.py":
            scripts.append(file.stem)
    
    for file in SCRIPTS_DIR.glob("*.sh"):
        scripts.append(file.stem)
    
    return sorted(scripts)

def get_script_path(script_name):
    """Get full path to a script"""
    # Try .py extension first
    py_path = SCRIPTS_DIR / f"{script_name}.py"
    if py_path.exists():
        return py_path
    
    # Try .sh extension
    sh_path = SCRIPTS_DIR / f"{script_name}.sh"
    if sh_path.exists():
        return sh_path
    
    return None

if __name__ == "__main__":
    print("Available scripts:")
    for script in list_scripts():
        print(f"  - {script}")