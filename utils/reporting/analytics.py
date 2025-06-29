from __future__ import annotations

import pandas as pd
from typing import Dict

"""Additional analytics utilities (equity curve, drawdown, expectancy)."""


# ------------------------------------------------------------------


def equity_curve(trades_df: pd.DataFrame, starting_balance: float = 0.0) -> pd.Series:  # noqa: D401
    """Return cumulative PnL series indexed by trade order."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    pnl = trades_df["Realised_PnL"].cumsum() + starting_balance
    pnl.index = trades_df.index
    return pnl


def drawdown_series(equity: pd.Series) -> pd.Series:  # noqa: D401
    if equity.empty:
        return equity
    peak = equity.cummax()
    dd = (equity - peak) / peak * 100
    return dd


def basic_trade_stats(trades_df: pd.DataFrame) -> Dict[str, float]:  # noqa: D401
    """Compute expectancy, win-rate, payoff ratio (R multiple level)."""
    if trades_df.empty:
        return {
            "expectancy": 0.0,
            "win_rate": 0.0,
            "payoff_ratio": 0.0,
            "avg_r_multiple": 0.0,
        }
    wins = trades_df[trades_df["Realised_PnL"] > 0]
    losses = trades_df[trades_df["Realised_PnL"] <= 0]
    win_rate = len(wins) / len(trades_df) if len(trades_df) else 0.0
    avg_win = wins["Realised_PnL"].mean() if not wins.empty else 0.0
    avg_loss = losses["Realised_PnL"].abs().mean() if not losses.empty else 0.0
    payoff = (avg_win / avg_loss) if avg_loss else 0.0
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
    return {
        "expectancy": round(expectancy, 2),
        "win_rate": round(win_rate * 100, 2),
        "payoff_ratio": round(payoff, 2),
        "avg_r_multiple": round(trades_df["PnL%"].mean() / 100, 2),
    }


__all__ = ["equity_curve", "drawdown_series", "basic_trade_stats"]
