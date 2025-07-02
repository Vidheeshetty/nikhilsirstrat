from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

import yaml

from strategies.sma_fractal_scalper.strategy import SmaFractalScalper
from strategies.sma_fractal_scalper.config import SmaFractalScalperConfig


logger = logging.getLogger(__name__)


class SmaFractalScalperPaperRunner:  # pylint: disable=too-few-public-methods
    """Consume live quote ticks and drive ``SmaFractalScalper`` in paper-trading.

    The runner is intentionally lightweight – it obtains *last_price* from the
    provided ``BrokerManager`` and forwards the value to ``strategy.on_quote``.
    Position sizing, order submission, and trade management are handled inside
    the strategy for now; future iterations can migrate these responsibilities
    to a shared trade-engine.
    """

    # ------------------------------------------------------------------
    def __init__(
        self,
        strategy_name: str,
        broker_manager: Any,
        broker_name: str,
        config_file: Optional[str] = None,
        instrument_id: Optional[str] = None,
    ) -> None:
        self.strategy_name = strategy_name
        self.broker_manager = broker_manager
        self.broker_name = broker_name
        self.config_file = config_file
        self.instrument_id = instrument_id  # may be filled during initialize()

        self._strategy: Optional[SmaFractalScalper] = None
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    async def initialize(self) -> None:  # noqa: D401
        """Prepare strategy instance and resolve instrument id."""
        # ------------------------------------------------------------------
        cfg_dict: Dict[str, Any] = {}
        if self.config_file and Path(self.config_file).exists():
            try:
                cfg_dict = yaml.safe_load(Path(self.config_file).read_text()) or {}
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to load strategy config %s – %s", self.config_file, exc)

        # Resolve instrument id ------------------------------------------------
        # Priority: explicit arg  > YAML field 'instrument_id' > env variable
        self.instrument_id = (
            self.instrument_id
            or cfg_dict.get("instrument_id")
            or cfg_dict.get("symbol")
            or "NIFTY23JULFUT"  # safe default for dry-run environments
        )

        # Build validated config dataclass ------------------------------------
        config_obj = SmaFractalScalperConfig(**{k: v for k, v in cfg_dict.items() if k != "instrument_id"})
        self._strategy = SmaFractalScalper(config_obj)
        logger.info("[%s] Strategy initialised for %s", self.strategy_name, self.instrument_id)

    # ------------------------------------------------------------------
    async def start(self) -> None:  # noqa: D401
        if self._running:
            return
        self._running = True
        # Optionally launch a background task to pull quotes if engine does not
        # call :py:meth:`process_market_update` explicitly. For now we rely on
        # the engine loop, so just log ready status.
        logger.info("[%s] PaperRunner started", self.strategy_name)

    # ------------------------------------------------------------------
    async def stop(self) -> None:  # noqa: D401
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("[%s] PaperRunner stopped", self.strategy_name)

    # ------------------------------------------------------------------
    async def process_market_update(self) -> None:  # noqa: D401
        """Fetch latest quote, aggregate to 1-minute bar, feed strategy."""
        if not self._running or self._strategy is None:
            return

        try:
            quote: Dict[str, Any] = await self.broker_manager.get_quote(
                self.instrument_id, broker_name=self.broker_name
            )
            last_price = quote.get("last_price")
            ts = datetime.utcnow()
            if last_price is None:
                return

            # ----------------------------------------------------------
            # Minute-bar aggregation
            # ----------------------------------------------------------
            minute_key = ts.replace(second=0, microsecond=0)
            bar = getattr(self, "_current_bar", None)
            if bar is None or bar["minute"] != minute_key:
                # Finalise previous bar --------------------------------
                if bar is not None:
                    self._emit_bar(bar)

                # Start new bar ----------------------------------------
                self._current_bar = {
                    "minute": minute_key,
                    "open": last_price,
                    "high": last_price,
                    "low": last_price,
                    "close": last_price,
                    "volume": quote.get("volume", 0),
                    "oi": quote.get("oi"),
                }
            else:
                # Update existing bar
                bar["high"] = max(bar["high"], last_price)
                bar["low"] = min(bar["low"], last_price)
                bar["close"] = last_price
                bar["volume"] += quote.get("volume", 0)
                if quote.get("oi") is not None:
                    bar["oi"] = quote["oi"]  # store last OI within minute

        except Exception as exc:  # pragma: no cover
            logger.error("[%s] Error in market update: %s", self.strategy_name, exc, exc_info=False)

    # ------------------------------------------------------------------
    def _emit_bar(self, bar_dict: Dict[str, Any]):
        """Convert dict to lightweight bar object and send to strategy."""
        class _Bar:
            __slots__ = ("open", "high", "low", "close", "volume", "oi", "timestamp")

            def __init__(self, d):
                self.open = d["open"]
                self.high = d["high"]
                self.low = d["low"]
                self.close = d["close"]
                self.volume = d.get("volume")
                self.oi = d.get("oi")
                self.timestamp = d["minute"].isoformat()

        bar_obj = _Bar(bar_dict)
        signal_before = len(getattr(self._strategy, "trades", []))
        self._strategy.on_bar(bar_obj)

        # If no trade made and no existing position, log rejection reason
        signal_after = len(getattr(self._strategy, "trades", []))
        if signal_after == signal_before:
            logger.debug(
                "[%s] Minute bar processed (O=%.2f H=%.2f L=%.2f C=%.2f V=%s OI=%s) – no signal",  # noqa: E501
                self.strategy_name,
                bar_obj.open,
                bar_obj.high,
                bar_obj.low,
                bar_obj.close,
                bar_obj.volume,
                bar_obj.oi,
            )

    # ------------------------------------------------------------------
    async def emergency_stop(self) -> None:  # noqa: D401
        if self._running and self._strategy is not None:
            try:
                self._strategy.on_stop()
            except Exception:
                pass
            await self.stop()

    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:  # noqa: D401
        trades_len = len(getattr(self._strategy, "trades", [])) if self._strategy else 0
        return {
            "enabled": self._running,
            "instrument": self.instrument_id,
            "trades": trades_len,
        } 