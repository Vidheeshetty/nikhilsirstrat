"""ND_TT_V4 breakout reversal strategy implementation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from utils.strategy.base_strategy import BaseStrategy

from .config import NdTtV4Config


@dataclass
class _SwingPoint:
    price: float
    index: int


class NdTtV4Strategy(BaseStrategy):
    """Replicates TradingView ND_TT_V4 logic within platform architecture."""

    config_class = NdTtV4Config

    def __init__(self, config: NdTtV4Config):
        super().__init__(config)
        self._last_top: Optional[_SwingPoint] = None
        self._last_bottom: Optional[_SwingPoint] = None
        self._position: int = 0
        self._entry_price: Optional[float] = None
        self._entry_side: Optional[str] = None
        self._entry_date: Optional[str] = None
        self._entry_reason: Optional[str] = None  # Store entry reason
        self._entry_oi: int = 0
        self._bar_index: int = -1
        self._current_date: Optional[str] = None
        self._current_oi: int = 0
        self._closes: Deque[float] = deque(maxlen=max(3, self.config.warmup_bars))
        self.trades: list[dict] = []

    # ------------------------------------------------------------------
    def on_bar(self, bar):  # noqa: D401
        """Process incoming OHLC bar."""
        close = float(getattr(bar, "close", None) or 0.0)
        high = float(getattr(bar, "high", close))
        low = float(getattr(bar, "low", close))
        open_price = float(getattr(bar, "open", close))
        
        # Extract date and time from bar object (date_str should be pre-formatted by runner)
        if hasattr(bar, 'date_str'):
            self._current_date = bar.date_str
        elif hasattr(bar, 'ts_event'):
            # Fallback: Convert nautilus timestamp (shouldn't be reached normally)
            from datetime import datetime
            self._current_date = datetime.fromtimestamp(bar.ts_event / 1_000_000_000).strftime('%Y-%m-%d')
        elif hasattr(bar, 'timestamp'):
            self._current_date = str(bar.timestamp)[:10]  # Extract date part only
        else:
            self._current_date = f"Bar_{self._bar_index + 1}"
        
        # Extract OI if available
        if hasattr(bar, 'oi'):
            self._current_oi = int(bar.oi)
        else:
            self._current_oi = 0
            
        self._process_bar(open_price, high, low, close)

    def on_quote(self, price):  # noqa: D401
        """Fallback when only quote (float) data is available."""
        price_f = float(price)
        self._process_bar(price_f, price_f, price_f, price_f)

    # ------------------------------------------------------------------
    def _process_bar(self, open_px: float, high_px: float, low_px: float, close_px: float) -> None:
        self._bar_index += 1

        prev_close = self._closes[-1] if len(self._closes) >= 1 else None
        prev2_close = self._closes[-2] if len(self._closes) >= 2 else None
        self._closes.append(close_px)

        if prev_close is None or prev2_close is None:
            return

        is_top = prev_close > prev2_close and prev_close > close_px
        is_bottom = prev_close < prev2_close and prev_close < close_px

        prev_index = self._bar_index - 1

        if is_top and (self._last_top is None or (prev_index - self._last_top.index) >= 2):
            self._last_top = _SwingPoint(price=prev_close, index=prev_index)
        if is_bottom and (
            self._last_bottom is None or (prev_index - self._last_bottom.index) >= 2
        ):
            self._last_bottom = _SwingPoint(price=prev_close, index=prev_index)

        buffer_pct = self.config.buffer_percentage
        top_buffer = (
            self._last_top.price * (1 + buffer_pct) if self._last_top is not None else None
        )
        bottom_buffer = (
            self._last_bottom.price * (1 - buffer_pct) if self._last_bottom is not None else None
        )

        top_breached = (
            top_buffer is not None
            and high_px >= top_buffer
            and self._last_top is not None
            and (self._bar_index - self._last_top.index) >= 2
        )
        bottom_breached = (
            bottom_buffer is not None
            and low_px <= bottom_buffer
            and self._last_bottom is not None
            and (self._bar_index - self._last_bottom.index) >= 2
        )

        if self._position == 0:
            if top_breached:
                reason = f"Top Buffer Breach (Swing: {self._last_top.price:.2f}, Buffer: {top_buffer:.2f}, High: {high_px:.2f})"
                self._enter_position("LONG", close_px, reason=reason)
            elif bottom_breached:
                reason = f"Bottom Buffer Breach (Swing: {self._last_bottom.price:.2f}, Buffer: {bottom_buffer:.2f}, Low: {low_px:.2f})"
                self._enter_position("SHORT", close_px, reason=reason)
            return

        if self._position > 0 and self._entry_price is not None:
            long_stop = self._entry_price * (1 - self.config.stop_loss_percentage)
            if bottom_breached:
                reason = f"Reversal to SHORT - Bottom Buffer Breach (Entry: {self._entry_price:.2f}, Buffer: {bottom_buffer:.2f}, Low: {low_px:.2f})"
                self._exit_position(close_px, reason=reason)
                entry_reason = f"Bottom Buffer Breach (Swing: {self._last_bottom.price:.2f}, Buffer: {bottom_buffer:.2f}, Low: {low_px:.2f})"
                self._enter_position("SHORT", close_px, reason=entry_reason)
                return
            if long_stop > (bottom_buffer or -float("inf")) and low_px <= long_stop:
                reason = f"Stop Loss Hit (Entry: {self._entry_price:.2f}, Stop: {long_stop:.2f}, Low: {low_px:.2f}, SL%: {self.config.stop_loss_percentage*100:.2f}%)"
                self._exit_position(long_stop, reason=reason)
                return

        if self._position < 0 and self._entry_price is not None:
            short_stop = self._entry_price * (1 + self.config.stop_loss_percentage)
            if top_breached:
                reason = f"Reversal to LONG - Top Buffer Breach (Entry: {self._entry_price:.2f}, Buffer: {top_buffer:.2f}, High: {high_px:.2f})"
                self._exit_position(close_px, reason=reason)
                entry_reason = f"Top Buffer Breach (Swing: {self._last_top.price:.2f}, Buffer: {top_buffer:.2f}, High: {high_px:.2f})"
                self._enter_position("LONG", close_px, reason=entry_reason)
                return
            if short_stop < (top_buffer or float("inf")) and high_px >= short_stop:
                reason = f"Stop Loss Hit (Entry: {self._entry_price:.2f}, Stop: {short_stop:.2f}, High: {high_px:.2f}, SL%: {self.config.stop_loss_percentage*100:.2f}%)"
                self._exit_position(short_stop, reason=reason)

    # ------------------------------------------------------------------
    def _enter_position(self, side: str, price: float, reason: str = "") -> None:
        qty = self.config.order_quantity
        self._position = 1 if side == "LONG" else -1
        self._entry_price = price
        self._entry_side = side
        self._entry_date = self._current_date
        self._entry_reason = reason  # Store the entry reason
        self._entry_oi = self._current_oi
        self.log.info(
            "ENTRY: %s x %.2f at %.2f on %s (OI: %d) | Reason: %s",
            side, qty, price, self._current_date, self._entry_oi, reason
        )

    def _exit_position(self, price: float, *, reason: str) -> None:
        if self._position == 0 or self._entry_price is None or self._entry_side is None:
            return
        trade = {
            "side": self._entry_side,
            "entry_price": self._entry_price,
            "entry_date": self._entry_date,
            "entry_reason": self._entry_reason,  # Include entry reason
            "entry_oi": self._entry_oi,
            "exit_price": price,
            "exit_date": self._current_date,
            "exit_reason": reason,  # Rename to exit_reason for clarity
            "exit_oi": self._current_oi,
            "qty": self.config.order_quantity,
        }
        direction = 1 if self._entry_side == "LONG" else -1
        trade["pnl"] = (price - self._entry_price) * trade["qty"] * direction
        pnl_pct = (trade["pnl"] / self._entry_price) * 100 if self._entry_price else 0.0
        self.trades.append(trade)
        self.log.info(
            "EXIT: %s at %.2f on %s | PnL: %.2f (%.2f%%) | OI: %d->%d | Duration: %s to %s | Reason: %s",
            self._entry_side,
            price,
            self._current_date,
            trade["pnl"],
            pnl_pct,
            self._entry_oi,
            self._current_oi,
            self._entry_date,
            self._current_date,
            reason,
        )
        self._position = 0
        self._entry_price = None
        self._entry_side = None
        self._entry_date = None
        self._entry_reason = None
        self._entry_oi = 0

