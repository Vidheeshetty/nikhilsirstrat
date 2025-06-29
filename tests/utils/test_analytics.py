import pandas as pd
from utils.reporting.analytics import equity_curve, drawdown_series, basic_trade_stats


def test_analytics_functions():
    trades = pd.DataFrame(
        {
            "Realised_PnL": [100, -50, 150, -30],
            "PnL%": [1.0, -0.5, 1.5, -0.3],
        }
    )
    eq = equity_curve(trades)
    dd = drawdown_series(eq)
    stats = basic_trade_stats(trades)

    assert len(eq) == 4
    assert (dd <= 0).all()
    assert "expectancy" in stats and isinstance(stats["expectancy"], float)
