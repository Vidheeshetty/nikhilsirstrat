import json
import subprocess
import sys
from pathlib import Path


def test_run_batch_backtest_cli(tmp_path):
    script = Path("scripts/run_batch_backtest.py").resolve()
    instruments = ["AAA.FUT.NSE", "BBB.FUT.NSE"]

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--instruments",
            *instruments,
            "--outfile",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["num_instruments"] == 2
