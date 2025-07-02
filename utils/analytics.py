from __future__ import annotations

"""Generic analytics helpers reused by reporting modules.

This thin wrapper exists so that high-level reporters can import
``utils.analytics`` without worrying about the exact sub-package where metric
functions live.  Over time you can move richer analytics here and keep
existing import paths stable.
"""

import math
from typing import List, Dict

__all__ = ["calculate_additional_metrics"]


def calculate_additional_metrics(series: List[float]) -> Dict[str, float]:  # noqa: D401
    """Return basic risk/performance metrics for an equity/PnL series.

    Parameters
    ----------
    series : list[float]
        Chronological series of *equity values* (e.g. cumulative PnL or
        portfolio value).  Must contain at least two points.

    Returns
    -------
    dict
        Keys: ``mdd_pct`` (max draw-down, %), ``sharpe`` (annualised Sharpe
        with 252 trading days), ``return_pct`` (simple % return over period).
    """

    if len(series) < 2:
        return {"mdd_pct": 0.0, "sharpe": 0.0, "return_pct": 0.0}

    # ------------------------------------------------------------------
    # Return % over entire period
    # ------------------------------------------------------------------
    return_pct = (series[-1] / series[0] - 1) * 100 if series[0] else 0.0

    # ------------------------------------------------------------------
    # Max draw-down
    # ------------------------------------------------------------------
    peak = series[0]
    max_dd = 0.0
    for v in series:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak else 0.0
        if dd > max_dd:
            max_dd = dd
    mdd_pct = max_dd * 100

    # ------------------------------------------------------------------
    # Simple Sharpe ratio using equity diffs as daily returns
    # ------------------------------------------------------------------
    rets = [series[i + 1] - series[i] for i in range(len(series) - 1)]
    if not rets:
        sharpe = 0.0
    else:
        avg_ret = sum(rets) / len(rets)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in rets) / len(rets))
        sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret else 0.0

    return {
        "return_pct": round(return_pct, 2),
        "mdd_pct": round(mdd_pct, 2),
        "sharpe": round(sharpe, 2),
    } 