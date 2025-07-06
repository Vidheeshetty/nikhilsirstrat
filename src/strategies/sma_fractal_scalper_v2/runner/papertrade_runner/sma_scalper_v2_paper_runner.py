from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

import yaml

from src.strategies.sma_fractal_scalper_v2.strategy import SmaFractalScalperV2
from src.strategies.sma_fractal_scalper_v2.config import SmaFractalScalperV2Config


logger = logging.getLogger(__name__)


class SmaFractalScalperV2PaperRunner:  # pylint: disable=too-few-public-methods
    """Consume live quote ticks and drive ``SmaFractalScalperV2`` in paper-trading.

    This runner demonstrates the pluggable architecture integration with the
    existing paper trading infrastructure. It follows the same pattern as the
    original runner but uses the new strategy with indicator and signal managers.
    
    The runner is intentionally lightweight – it obtains *last_price* from the
    provided ``BrokerManager`` and forwards the value to ``strategy.on_bar``.
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

        self._strategy: Optional[SmaFractalScalperV2] = None
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
                logger.warning(
                    "Failed to load strategy config %s – %s", self.config_file, exc
                )

        # Resolve instrument id ------------------------------------------------
        # Priority: explicit arg  > YAML field 'instrument_id' > env variable
        self.instrument_id = (
            self.instrument_id
            or cfg_dict.get("instrument_id")
            or cfg_dict.get("symbol")
            or "NIFTY23JULFUT"  # safe default for dry-run environments
        )

        # Set default config paths if not provided
        strategy_dir = Path(__file__).parent.parent.parent
        if 'indicators_config_path' not in cfg_dict:
            cfg_dict['indicators_config_path'] = str(strategy_dir / 'indicators.yaml')
        if 'signals_config_path' not in cfg_dict:
            cfg_dict['signals_config_path'] = str(strategy_dir / 'signals.yaml')

        # Build validated config dataclass ------------------------------------
        config_obj = SmaFractalScalperV2Config(
            **{k: v for k, v in cfg_dict.items() if k not in ['instrument_id', 'symbol']}
        )
        
        # Initialize strategy with pluggable architecture
        self._strategy = SmaFractalScalperV2(config_obj)
        
        # Set broker manager and instrument for trading operations
        if hasattr(self._strategy, 'set_broker_manager'):
            self._strategy.set_broker_manager(self.broker_manager)
        if hasattr(self._strategy, 'set_instrument_id'):
            self._strategy.set_instrument_id(self.instrument_id)

        # Perform historical warmup if enabled
        if config_obj.historical_warmup:
            await self._perform_historical_warmup()

        logger.info(
            "[%s] Strategy V2 initialised for %s with pluggable architecture", 
            self.strategy_name, 
            self.instrument_id
        )

    # ------------------------------------------------------------------
    async def _perform_historical_warmup(self) -> None:
        """Perform historical data warmup for indicators."""
        try:
            # Get warmup requirements
            warmup_reqs = self._strategy.get_warmup_requirements()
            if not warmup_reqs:
                logger.info("[%s] No warmup requirements, strategy ready", self.strategy_name)
                return
            
            # Calculate total bars needed
            max_bars = max(warmup_reqs.values()) if warmup_reqs else 0
            total_bars_needed = max_bars + 10  # Add buffer
            
            logger.info("[%s] Warmup requirements: %s, loading %d bars", 
                       self.strategy_name, warmup_reqs, total_bars_needed)
            
            # TODO: Integrate with historical data loader
            # For now, we'll simulate some historical bars
            historical_bars = self._generate_sample_warmup_data(total_bars_needed)
            
            # Warm up the strategy
            self._strategy.warmup_indicators(historical_bars)
            
            logger.info("[%s] ✅ Strategy warmed up and ready to trade", self.strategy_name)
            
        except Exception as exc:
            logger.error("[%s] Error during warmup: %s", self.strategy_name, exc)
            # Continue without warmup
    
    def _generate_sample_warmup_data(self, num_bars: int) -> list:
        """Generate sample historical data for warmup (placeholder)."""
        # This is a placeholder - in production, this would load real historical data
        base_price = 1000.0
        bars = []
        
        for i in range(num_bars):
            price = base_price + (i * 0.1) + (i % 10) * 0.05
            bar = {
                'timestamp': datetime.utcnow(),
                'open': price - 0.05,
                'high': price + 0.1,
                'low': price - 0.1,
                'close': price,
                'volume': 1000 + i
            }
            bars.append(bar)
        
        return bars

    # ------------------------------------------------------------------
    async def start(self) -> None:  # noqa: D401
        if self._running:
            return
        self._running = True
        # Optionally launch a background task to pull quotes if engine does not
        # call :py:meth:`process_market_update` explicitly. For now we rely on
        # the engine loop, so just log ready status.
        logger.info("[%s] PaperRunner V2 started", self.strategy_name)

    # ------------------------------------------------------------------
    async def stop(self) -> None:  # noqa: D401
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("[%s] PaperRunner V2 stopped", self.strategy_name)

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
            logger.error(
                "[%s] Error in market update: %s",
                self.strategy_name,
                exc,
                exc_info=False,
            )

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
        if self._strategy is None:
            return
            
        # Track signals before processing
        signal_before = getattr(self._strategy, 'last_signal', None)
        
        # Process bar through the new pluggable architecture
        signal_result = self._strategy.on_bar({
            'timestamp': bar_obj.timestamp,
            'open': bar_obj.open,
            'high': bar_obj.high,
            'low': bar_obj.low,
            'close': bar_obj.close,
            'volume': bar_obj.volume
        })

        # Check for pending orders and submit them
        asyncio.create_task(self._process_pending_orders(signal_result))

        # Log bar processing result
        signal_after = getattr(self._strategy, 'last_signal', None)
        if signal_result:
            logger.debug(
                "[%s] Minute bar processed (O=%.2f H=%.2f L=%.2f C=%.2f V=%s OI=%s) – SIGNAL: %s",
                self.strategy_name,
                bar_obj.open,
                bar_obj.high,
                bar_obj.low,
                bar_obj.close,
                bar_obj.volume,
                bar_obj.oi,
                signal_result.get('signal_type', 'UNKNOWN')
            )
        else:
            logger.debug(
                "[%s] Minute bar processed (O=%.2f H=%.2f L=%.2f C=%.2f V=%s OI=%s) – no signal",
                self.strategy_name,
                bar_obj.open,
                bar_obj.high,
                bar_obj.low,
                bar_obj.close,
                bar_obj.volume,
                bar_obj.oi,
            )

    async def _process_pending_orders(self, signal_result: Optional[Dict[str, Any]]):
        """Process any pending orders from the strategy signal."""
        if not signal_result:
            return
            
        try:
            # Convert signal to order if needed
            signal_type = signal_result.get('signal_type')
            if signal_type in ['LONG', 'SHORT']:
                await self._submit_signal_order(signal_result)

        except Exception as exc:
            logger.error(
                "[%s] Error processing signal orders: %s", self.strategy_name, exc
            )

    async def _submit_signal_order(self, signal_result: Dict[str, Any]):
        """Submit an order based on strategy signal."""
        try:
            # Import order types for paper trading
            from src.brokers.base import Order, OrderType, TransactionType, OrderStatus
            from datetime import datetime
            import uuid

            # Determine transaction type
            signal_type = signal_result['signal_type']
            transaction_type = (
                TransactionType.BUY if signal_type == "LONG" else TransactionType.SELL
            )

            # Generate order ID
            order_id = f"V2_{self.strategy_name}_{uuid.uuid4().hex[:8]}"

            # Create order object
            order = Order(
                order_id=order_id,
                instrument_id=self.instrument_id,
                quantity=1,  # TODO: Calculate quantity based on risk management
                price=None,  # Market order for now
                order_type=OrderType.MARKET,
                transaction_type=transaction_type,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            # Submit to broker
            broker_order_id = await self.broker_manager.place_order(order)

            logger.info(
                "[%s] ✅ V2 Signal order submitted: %s %s @ market price (confidence: %.2f) - Broker ID: %s",
                self.strategy_name,
                signal_type,
                self.instrument_id,
                signal_result.get('confidence', 0.0),
                broker_order_id,
            )

        except Exception as exc:
            logger.error(
                "[%s] ❌ Failed to submit V2 signal order: %s",
                self.strategy_name,
                exc,
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
        """Get enhanced status including pluggable architecture information."""
        base_status = {
            "enabled": self._running,
            "instrument": self.instrument_id,
            "strategy_name": "SmaFractalScalperV2",
            "runner_class": "SmaFractalScalperV2PaperRunner"
        }
        
        if self._strategy:
            strategy_status = self._strategy.get_status()
            base_status.update({
                "warmup_complete": strategy_status.get('warmup_complete', False),
                "indicators": len(strategy_status.get('indicators', {})),
                "signal_generators": len(strategy_status.get('signal_generators', {})),
                "last_signal": strategy_status.get('last_signal'),
            })
        
        return base_status
    
    # ------------------------------------------------------------------
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart configuration for visualization."""
        if self._strategy:
            return self._strategy.get_chart_config()
        return {}
    
    # ------------------------------------------------------------------
    def enable_indicator(self, indicator_name: str) -> bool:
        """Enable a specific indicator dynamically."""
        if self._strategy:
            return self._strategy.enable_indicator(indicator_name)
        return False
    
    def disable_indicator(self, indicator_name: str) -> bool:
        """Disable a specific indicator dynamically."""
        if self._strategy:
            return self._strategy.disable_indicator(indicator_name)
        return False
    
    def enable_signal_generator(self, generator_name: str) -> bool:
        """Enable a specific signal generator dynamically."""
        if self._strategy:
            return self._strategy.enable_signal_generator(generator_name)
        return False
    
    def disable_signal_generator(self, generator_name: str) -> bool:
        """Disable a specific signal generator dynamically."""
        if self._strategy:
            return self._strategy.disable_signal_generator(generator_name)
        return False 