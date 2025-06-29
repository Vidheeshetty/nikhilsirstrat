"""
Setup file for Jupyter notebooks in the 'Jupyter Code' folder.
This file adds the necessary paths to import modules from the src directory.
"""

import sys
import os


def setup_paths():
    """Add the src directory to Python path for importing strategy modules."""
    # Get the current working directory (should be the Jupyter Code folder)
    current_dir = os.getcwd()

    # Go up one level to the project root, then into src
    project_root = os.path.dirname(current_dir)
    src_path = os.path.join(project_root, "src")

    # Add to sys.path if not already there
    if src_path not in sys.path:
        sys.path.append(src_path)
        print(f"✅ Added to sys.path: {src_path}")
    else:
        print(f"ℹ️  Path already exists: {src_path}")

    # Also add the project root for accessing data and config files
    if project_root not in sys.path:
        sys.path.append(project_root)
        print(f"✅ Added to sys.path: {project_root}")

    print(f"📁 Current working directory: {current_dir}")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Source directory: {src_path}")

    # Verify the src directory exists
    if not os.path.exists(src_path):
        print(f"⚠️  Warning: src directory not found at {src_path}")
        return None, None

    return src_path, project_root


# Auto-run setup when imported
if __name__ == "__main__":
    setup_paths()
else:
    # When imported as a module, run setup automatically
    src_path, project_root = setup_paths()
