from __future__ import annotations

import math
from typing import List

"""Performance metric utilities (pure Python)."""


def calculate_metrics(prices: List[float]) -> dict[str, float]:  # noqa: D401
    if len(prices) < 2:
        return {
            "pnl": 0.0,
            "return_pct": 0.0,
            "mdd_pct": 0.0,
            "max_drawdown_pct": 0.0,  # legacy alias
            "sharpe": 0.0,
        }

    pnl = prices[-1] - prices[0]
    return_pct = (prices[-1] / prices[0] - 1) * 100

    # Max drawdown
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak
        if dd > max_dd:
            max_dd = dd
    mdd_pct = max_dd * 100

    # Daily returns as simple diff for Sharpe (assumes 1 unit time step)
    rets = [prices[i + 1] / prices[i] - 1 for i in range(len(prices) - 1)]
    avg_ret = sum(rets) / len(rets)
    std_ret = (
        math.sqrt(sum((r - avg_ret) ** 2 for r in rets) / len(rets)) if rets else 0.0
    )
    sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret else 0.0

    return {
        "pnl": pnl,
        "return_pct": return_pct,
        "mdd_pct": mdd_pct,
        "max_drawdown_pct": mdd_pct,  # legacy alias
        "sharpe": sharpe,
    }


__all__ = ["calculate_metrics"]
