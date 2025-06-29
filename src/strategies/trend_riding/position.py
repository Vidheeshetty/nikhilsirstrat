from __future__ import annotations

"""Position sizing logic for Trend-Riding – placeholder implementation."""


def calculate_size(
    capital: float, risk_per_trade_pct: float, price: float, sl_pct: float
) -> int:  # noqa: D401,E501
    """Basic fixed-fractional sizing.

    Args:
        capital: total account capital.
        risk_per_trade_pct: fraction of capital to risk per trade (0.01 = 1%).
        price: current instrument price.
        sl_pct: distance from entry to stop as percentage.
    Returns:
        Number of contracts/shares; returns 0 if inputs invalid.
    """
    if price <= 0 or sl_pct <= 0:
        return 0
    risk_amount = capital * risk_per_trade_pct
    per_unit_risk = price * sl_pct
    if per_unit_risk == 0:
        return 0
    return int(risk_amount / per_unit_risk)


__all__ = ["calculate_size"]
