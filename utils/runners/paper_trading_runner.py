from __future__ import annotations

"""Stub PaperTradingStrategyRunner

A placeholder so the paper-trading CLI can boot in *dry-run* mode even before
full live-runner integration is complete.
"""

from typing import Any

__all__ = ["PaperTradingStrategyRunner"]


class PaperTradingStrategyRunner:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        strategy_name: str,
        broker_manager: Any,
        broker_name: str,
        config_file: str | None = None,
        **_: Any,
    ):  # noqa: D401
        self.strategy_name = strategy_name
        self.broker_manager = broker_manager
        self.broker_name = broker_name
        self.config_file = config_file

    async def initialize(self):  # noqa: D401
        # Future: load strategy class, compile indicators, etc.
        return None

    async def start(self):  # noqa: D401
        # In a real implementation, subscribe to broker stream & drive strategy.
        return None

    async def stop(self):  # noqa: D401
        return None

    # ------------------------------------------------------------------
    async def process_market_update(self):  # noqa: D401
        """Stub hook called every engine loop; does nothing for dry-run."""
        return None

    async def emergency_stop(self):  # noqa: D401
        """Called when global risk limits breached – no-op stub."""
        return None

    def get_status(self):  # noqa: D401
        return {
            "enabled": True,
            "positions": 0,
            "pnl": 0.0,
        } 