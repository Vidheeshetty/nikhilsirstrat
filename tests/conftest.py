import pytest
from pathlib import Path
import sys
import asyncio
import inspect

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure test log directory exists so pytest can write the log file specified
Path("testlogs").mkdir(parents=True, exist_ok=True)


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


# -----------------------------------------------------------------------------
# Minimal asyncio support (fallback when pytest-asyncio is missing)
# -----------------------------------------------------------------------------
def pytest_pycollect_makeitem(collector, name, obj):  # pylint: disable=unused-argument
    """Wrap async test functions into sync wrappers so they run without pytest-asyncio.

    This fallback allows the test-suite to execute ``async def`` functions even
    if the *pytest-asyncio* plugin isn't present in the environment.
    """
    if inspect.iscoroutinefunction(obj):

        async def _async_wrapper(*args, **kwargs):  # type: ignore[override]
            return await obj(*args, **kwargs)

        def _sync_runner(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_async_wrapper(*args, **kwargs))

        return pytest.Function.from_parent(collector, name=name, callobj=_sync_runner)

    # Let Pytest use default collection for non-async callables.
    return None
