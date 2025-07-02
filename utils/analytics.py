"""
Analytical utilities for trading metrics calculation.

This module provides functions to calculate additional trading metrics
beyond the standard ones provided by NautilusTrader's built-in analytics.
"""

import math
from typing import List, Dict

__all__ = ["calculate_additional_metrics"]


def calculate_additional_metrics(trades: List[Dict]) -> Dict:
    """Calculate additional metrics from a list of trade dictionaries.

    Args:
        trades: List of trade dictionaries containing PnL data

    Returns:
        Dictionary with calculated metrics including win rate, avg win/loss, etc.
    """
    if not trades:
        return {}

    pnls = [
        trade.get("Realised_PnL", 0)
        for trade in trades
        if trade.get("Realised_PnL") is not None
    ]

    if not pnls:
        return {}

    winning_trades = [pnl for pnl in pnls if pnl > 0]
    losing_trades = [pnl for pnl in pnls if pnl < 0]

    total_trades = len(pnls)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)

    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
    avg_win = sum(winning_trades) / win_count if win_count > 0 else 0
    avg_loss = sum(losing_trades) / loss_count if loss_count > 0 else 0

    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    # Calculate maximum drawdown
    cumulative_pnl = 0
    peak = 0
    max_drawdown = 0

    for pnl in pnls:
        cumulative_pnl += pnl
        if cumulative_pnl > peak:
            peak = cumulative_pnl
        drawdown = peak - cumulative_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
    }
