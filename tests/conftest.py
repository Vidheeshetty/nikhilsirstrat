import pytest
import shutil
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

@pytest.fixture(scope="function")
def temp_test_dir(tmp_path_factory):
    """
    Provides a temporary directory for tests.
    Automatically cleaned up after each test function.
    """
    temp_dir = tmp_path_factory.mktemp("test_run")
    yield temp_dir
    # Cleanup logic (pytest handles cleanup of tmp_path_factory.mktemp automatically)
    # shutil.rmtree(temp_dir) 