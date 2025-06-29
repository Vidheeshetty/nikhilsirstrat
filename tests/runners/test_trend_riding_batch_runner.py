from strategies.trend_riding.runner.backtest_runner.batch_runner import (
    TrendRidingBatchRunner,
)


def test_trend_riding_batch_runner():
    instruments = ["AAA.FUT.NSE", "BBB.FUT.NSE", "CCC.FUT.NSE"]
    runner = TrendRidingBatchRunner(max_workers=2)
    summary = runner.run(instruments)

    assert summary["num_instruments"] == 3
    assert len(summary["results"]) == 3
    # Total pnl should be positive given monotonically rising stub prices
    assert summary["total_pnl"] > 0
