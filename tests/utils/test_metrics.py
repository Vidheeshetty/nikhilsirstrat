from utils.runners.metrics import calculate_metrics


def test_calculate_metrics():
    prices = [100, 102, 101, 105, 110]
    m = calculate_metrics(prices)
    assert m["pnl"] == 10
    assert m["return_pct"] > 0
    assert m["max_drawdown_pct"] >= 0
    assert "sharpe" in m
