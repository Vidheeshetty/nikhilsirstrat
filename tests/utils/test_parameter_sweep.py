import pandas as pd
from utils.experiments import run_parameter_sweep
from strategies.swing_range_expansion.runner.backtest_runner import (
    SwingRangeExpansionBacktestRunner,
)


def test_parameter_sweep_runs():
    grid = {"nr_lookback": [5], "target_rr": [1.5]}
    df = run_parameter_sweep(
        SwingRangeExpansionBacktestRunner, grid, ["AAA.FUT.NSE"], workers=1
    )
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "nr_lookback" in df.columns

    # Add more assertions as needed
