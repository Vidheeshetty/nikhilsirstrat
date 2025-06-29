import pandas as pd
from strategies.swing_range_expansion.strategy import SwingRangeExpansionStrategy
from strategies.swing_range_expansion.config import SwingRangeConfig


def test_nr7_and_trade_generation():
    # Fabricate deterministic bars where day 6 is NR7 and breakout next day
    highs = [110, 115, 120, 125, 130, 131, 140, 150, 160, 170]
    lows = [100, 105, 110, 115, 120, 121, 130, 140, 150, 160]
    closes = [105, 110, 115, 120, 125, 126, 135, 145, 155, 165]
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    df["date"] = pd.RangeIndex(len(df))

    cfg = SwingRangeConfig(nr_lookback=7, max_bars_in_trade=2)
    strat = SwingRangeExpansionStrategy(cfg)
    trades = strat.generate_trades(df, "TEST.FUT")

    # Expect exactly one trade triggered on bar index 7 (breakout)
    assert len(trades) == 1
    tr = trades[0]
    assert tr["Trade_Type"] == "Long"
    # Realised PnL should be positive as prices increase
    assert tr["Realised_PnL"] > 0
