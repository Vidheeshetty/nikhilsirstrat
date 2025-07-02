# Quick setup for Jupyter notebooks - Copy and paste this into a notebook cell

import sys
import os

# Get current directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")

# Determine project structure
if os.path.basename(current_dir) == "Jupyter Code":
    # We're in Jupyter Code folder, go up one level
    project_root = os.path.dirname(current_dir)
    src_path = os.path.join(project_root, "src")
else:
    # We're in project root or somewhere else
    project_root = current_dir
    src_path = os.path.join(project_root, "src")

# Add paths to sys.path
paths_added = []

if src_path not in sys.path and os.path.exists(src_path):
    sys.path.append(src_path)
    paths_added.append(src_path)
    print(f"✅ Added src path: {src_path}")

if project_root not in sys.path:
    sys.path.append(project_root)
    paths_added.append(project_root)
    print(f"✅ Added project root: {project_root}")

if not paths_added:
    print("ℹ️  All paths already in sys.path")

print("\n📁 Project structure:")
print(f"   Project root: {project_root}")
print(f"   Source directory: {src_path}")
print(f"   Current working directory: {os.getcwd()}")

print("\n🔧 Ready to import modules!")
print("   You can now use: from strategies.my_nse_strategy import MyNSEStrategy")
