from strategies.trend_riding.exit import should_exit


def test_should_exit_tp():
    entry_price = 100
    prices = [95, 100, 105]
    assert should_exit(prices, entry_price, sl_pct=0.05, tp_pct=0.04) is True  # TP hit


def test_should_exit_sl():
    entry_price = 100
    prices = [100, 95]
    assert should_exit(prices, entry_price, sl_pct=0.05, tp_pct=0.1) is True  # SL hit


def test_should_exit_false():
    entry_price = 100
    prices = [100, 101]
    assert should_exit(prices, entry_price, sl_pct=0.05, tp_pct=0.1) is False
