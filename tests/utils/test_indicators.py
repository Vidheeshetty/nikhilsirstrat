from utils.strategy.indicators import sma, ema


def test_sma():
    series = list(range(1, 11))  # 1..10
    assert sma(series, 5) == 8.0


def test_ema():
    series = [1, 2, 3, 4, 5, 6]
    val = ema(series, 3)
    assert val > 0  # just ensure it returns numeric
    # For sequence 1..6 and period 3, EMA should be 5.0
    assert abs(val - 5.0) < 0.01
