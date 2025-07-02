from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .enums import Direction, ExitReason

"""Trade record structures and utilities for strategy implementations."""


@dataclass
class TradeRecord:
    """Standard trade record structure used across strategies."""

    instrument: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    direction: Direction
    exit_reason: ExitReason
    position_size: int = 1
    stop_price: float = 0.0
    target_price: float = 0.0
    entry_index: Optional[int] = None
    exit_index: Optional[int] = None

    @property
    def trade_type(self) -> str:
        """Get trade type as string for backward compatibility."""
        return self.direction.value

    @property
    def pnl(self) -> float:
        """Calculate raw P&L for the trade."""
        raw_pnl = self.exit_price - self.entry_price
        if self.direction == Direction.SHORT:
            raw_pnl = -raw_pnl
        return raw_pnl * self.position_size

    @property
    def pnl_pct(self) -> float:
        """Calculate P&L percentage."""
        if self.entry_price == 0:
            return 0.0
        return (self.pnl / (self.entry_price * self.position_size)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert trade record to dictionary format."""
        return {
            "Instrument": self.instrument,
            "Entry_Date": self.entry_date,
            "Trade_Type": self.trade_type,
            "Exit_Reason": self.exit_reason.value,
            "Entry_Price": round(self.entry_price, 2),
            "Exit_Date": self.exit_date,
            "Exit_Price": round(self.exit_price, 2),
            "Position_Size": self.position_size,
            "Threshold": self.entry_price,  # breakout level
            "SL_Price": round(self.stop_price, 2),
            "Target_Price": round(self.target_price, 2),
            "Realised_PnL": round(self.pnl, 2),
            "PnL%": round(self.pnl_pct, 2),
            "Entry_Index": self.entry_index,
            "Exit_Index": self.exit_index,
            "Cum_PnL": None,  # filled by enrich_trades later
        }


def enrich_trades_with_cumulative_pnl(trades: List[TradeRecord]) -> List[TradeRecord]:
    """Add cumulative P&L to trade records.

    Args:
        trades: List of trade records

    Returns:
        List of trade records with cumulative P&L added
    """
    cumulative_pnl = 0.0
    enriched_trades = []

    for trade in trades:
        cumulative_pnl += trade.pnl
        # Create a copy with cumulative PnL
        trade_dict = trade.to_dict()
        trade_dict["Cum_PnL"] = round(cumulative_pnl, 2)
        enriched_trades.append(trade)

    return enriched_trades


def calculate_trade_metrics(trades: List[TradeRecord]) -> Dict[str, Any]:
    """Calculate summary metrics for a list of trades.

    Args:
        trades: List of trade records

    Returns:
        Dictionary with trade metrics
    """
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_win": 0.0,
            "max_loss": 0.0,
            "profit_factor": 0.0,
        }

    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl < 0]

    total_wins = sum(t.pnl for t in winning_trades)
    total_losses = abs(sum(t.pnl for t in losing_trades))

    return {
        "total_trades": len(trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": len(winning_trades) / len(trades) * 100,
        "total_pnl": sum(t.pnl for t in trades),
        "avg_win": total_wins / len(winning_trades) if winning_trades else 0.0,
        "avg_loss": total_losses / len(losing_trades) if losing_trades else 0.0,
        "max_win": max(t.pnl for t in winning_trades) if winning_trades else 0.0,
        "max_loss": min(t.pnl for t in losing_trades) if losing_trades else 0.0,
        "profit_factor": total_wins / total_losses
        if total_losses > 0
        else float("inf"),
    }


def trades_to_dict_list(trades: List[TradeRecord]) -> List[Dict[str, Any]]:
    """Convert list of trade records to list of dictionaries.

    Args:
        trades: List of trade records

    Returns:
        List of trade dictionaries
    """
    return [trade.to_dict() for trade in trades]


__all__ = [
    "TradeRecord",
    "enrich_trades_with_cumulative_pnl",
    "calculate_trade_metrics",
    "trades_to_dict_list",
]
