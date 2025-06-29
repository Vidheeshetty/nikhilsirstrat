import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/run_backtest.py").resolve()


def _run_cli(args):
    return subprocess.check_output([sys.executable, str(SCRIPT), *args], text=True)


def test_cli_single():
    out = _run_cli(["--instrument_id", "AAA.FUT.NSE"])
    data = json.loads(out)
    assert data["instrument_id"] == "AAA.FUT.NSE"


def test_cli_all_default():
    # With no args it should run ALL (falls back to synthetic list len>=1)
    out = _run_cli([])
    data = json.loads(out)
    if "num_instruments" in data:
        assert data["num_instruments"] >= 1
    else:
        # Single instrument fallback
        assert "instrument_id" in data
