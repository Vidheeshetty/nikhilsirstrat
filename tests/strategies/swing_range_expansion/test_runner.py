from strategies.swing_range_expansion.runner.backtest_runner import (
    SwingRangeExpansionBacktestRunner,
)


def test_runner_returns_metrics():
    runner = SwingRangeExpansionBacktestRunner()
    result = runner.run("AAA.FUT.NSE")

    assert "pnl" in result
    assert "mdd_pct" in result or "max_drawdown_pct" in result
    assert "trades" in result
    # At least dummy result list
    assert isinstance(result["trades"], list)
