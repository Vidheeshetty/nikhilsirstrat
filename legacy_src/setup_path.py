import os
import sys
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Add root directory to Python path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Add src to Python path
src_path = os.path.join(ROOT_DIR, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

print(f"Added to Python path: {ROOT_DIR}")
print(f"Current Python path: {sys.path}")
