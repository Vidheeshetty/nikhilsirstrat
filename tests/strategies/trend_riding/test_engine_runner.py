from strategies.trend_riding.strategy import TrendRidingStrategy
from strategies.trend_riding.runner.backtest_runner.engine import BacktestEngine
from strategies.trend_riding.config import TrendRidingConfig


def test_strategy_handles_quotes(tmp_path):
    cfg = TrendRidingConfig(instrument_id="TEST_FUT.NSE")
    strat = TrendRidingStrategy(config=cfg)
    engine = BacktestEngine(on_quote=strat.on_quote)

    prices = [float(p) for p in range(1, 40)]  # quite arbitrary
    engine.run(prices)

    # Strategy should have processed all prices and stored them internally
    assert len(strat._prices) == len(prices)  # pylint: disable=protected-access
