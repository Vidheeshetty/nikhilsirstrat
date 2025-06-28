from strategies.trend_riding.entry import should_enter


def test_should_enter_true():
    prices = list(range(1, 21))  # 1..20
    assert should_enter(prices, period=5) is True


def test_should_enter_false():
    prices = [10] * 20  # flat price
    assert should_enter(prices, period=5) is False
