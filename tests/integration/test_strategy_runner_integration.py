from strategies.trend_riding.strategy import TrendRidingStrategy
from strategies.trend_riding.config import TrendRidingConfig
from strategies.trend_riding.runner.backtest_runner.engine import BacktestEngine


def test_run_strategy_end_to_end():
    # Generate a sequence of prices that trends upward
    prices = list(range(50, 100))

    cfg = TrendRidingConfig(instrument_id="TEST_FUT.NSE")
    strat = TrendRidingStrategy(cfg)

    engine = BacktestEngine(on_quote=strat.on_quote)
    engine.run(prices)

    # Strategy should at least have stored price history
    assert len(strat._prices) == len(prices)  # pylint: disable=protected-access
