"""
MyNSEStrategy - NSE Options Trading Strategy

This module implements a breakout-based options trading strategy for the National Stock Exchange (NSE).
The strategy is specifically designed for BANKNIFTY options with comprehensive risk management
and dynamic position management.

Strategy Overview:
    - Entry Logic: Breakout-based entry using rolling window price analysis
    - Filters: Implied volatility and open interest filters for quality signals
    - Risk Management: Dynamic stop-loss, take-profit, and trailing stop-loss
    - Position Management: Breakeven triggers and end-of-day position management

Key Features:
    - Rolling window breakout detection (configurable lookback period)
    - Implied volatility threshold filtering
    - Open interest change filtering
    - Dynamic stop-loss with trailing capability
    - Take-profit targets with percentage-based calculations
    - Breakeven stop-loss adjustment
    - End-of-day forced position closure

Author: Trading Strategy Developer
Version: 1.0.0
"""

from nautilus_trader.trading.strategy import Strategy  # Import base strategy class
from nautilus_trader.model import InstrumentId, Quantity  # Import trading model objects
from nautilus_trader.model.enums import OrderSide, TimeInForce  # Import trading enums
from nautilus_trader.model.events import PositionOpened, OrderFilled, PositionClosed  # Import trading events
from nautilus_trader.core.message import Event  # Import event base class
from nautilus_trader.model import QuoteTick  # Import quote tick data
from nautilus_trader.model.objects import Price  # Import price object

# Import configuration from config module
try:
    from .config import MyNSEStrategyConfig
except ImportError:
    # Fallback for direct execution
    from config import MyNSEStrategyConfig

import pandas as pd  # Import pandas for data manipulation
from datetime import time  # Import time for end-of-day logic
from collections import deque  # Import deque for rolling window
import os  # Import os for file operations


class MyNSEStrategy(Strategy):
    """
    NSE Options Trading Strategy with Breakout Logic.
    
    This strategy implements a breakout-based trading approach for NSE options,
    specifically designed for BANKNIFTY options. It uses rolling window analysis
    to detect price breakouts and applies multiple filters for signal quality.
    
    Strategy Logic:
        1. Entry: Price breaks above rolling window high with buffer
        2. Filters: Implied volatility and open interest change thresholds
        3. Risk Management: Dynamic stop-loss, take-profit, and trailing stops
        4. Exit: Stop-loss, take-profit, breakeven, or end-of-day closure
    
    Risk Management Features:
        - Initial stop-loss at rolling window low
        - Take-profit at configurable percentage
        - Trailing stop-loss based on new lows
        - Breakeven stop-loss after price gain
        - End-of-day forced position closure
    
    Attributes:
        in_trade: Boolean flag indicating if currently in a position
        position: Current position object
        entry_price: Entry price for current position
        sl_price: Current stop-loss price
        tp_price: Current take-profit price
        position_open_time: Timestamp when position was opened
        breakeven_triggered: Flag indicating if breakeven stop-loss is active
        direction: Position direction ("long" or "short")
        rolling_last: Rolling window of recent prices
        trades: List of completed trades
        current_trade: Current trade details
        order_count: Order counter for tracking
        active_orders: Dictionary of active orders
        meta_df: DataFrame containing metadata (IV/OI)
    """
    
    # Class attribute to reference the config class
    config_class = MyNSEStrategyConfig  # Reference to configuration class from config module
    
    def __init__(self, config: MyNSEStrategyConfig):
        """
        Initialize the MyNSEStrategy.
        
        Args:
            config: Strategy configuration object containing all parameters
        """
        super().__init__(config=config)  # Initialize parent strategy class
        
        # Position Management
        self.in_trade = False  # Flag indicating if currently in a trading position
        """Flag indicating if currently in a trading position."""
        
        self.position = None  # Current position object
        """Current position object."""
        
        self.entry_price = None  # Entry price for the current position
        """Entry price for the current position."""
        
        self.sl_price = None  # Current stop-loss price
        """Current stop-loss price."""
        
        self.tp_price = None  # Current take-profit price
        """Current take-profit price."""
        
        self.position_open_time = None  # Timestamp when the current position was opened
        """Timestamp when the current position was opened."""
        
        self.breakeven_triggered = False  # Flag indicating if breakeven stop-loss has been triggered
        """Flag indicating if breakeven stop-loss has been triggered."""
        
        self.direction = None  # Current position direction ('long' or 'short')
        """Current position direction ('long' or 'short')."""
        
        # Technical Analysis
        self.rolling_last = deque(maxlen=self.config.lookback_intervals)  # Rolling window of recent prices
        """Rolling window of recent prices for breakout detection."""
        
        # Trade Tracking
        self.trades = []  # List of completed trades for analysis
        """List of completed trades for analysis."""
        
        self.current_trade = None  # Current trade details being tracked
        """Current trade details being tracked."""
        
        self.order_count = 0  # Counter for tracking order sequence
        """Counter for tracking order sequence."""
        
        self.active_orders = {}  # Dictionary of active orders by order ID
        """Dictionary of active orders by order ID."""
        
        # Load metadata for IV/OI filtering
        self._load_metadata()  # Load implied volatility and open interest data

    def _load_metadata(self):
        """
        Load metadata from the parquet catalog for implied volatility and open interest data.
        
        This method loads metadata files containing implied volatility and open interest
        information for each tick, enabling filtering of trading signals based on
        market conditions.
        
        The metadata is stored in a multi-index DataFrame for fast lookups during
        tick processing.
        """
        path = self.config.meta_catalog_path  # Get metadata catalog path from config
        
        # Validate metadata path
        if not os.path.exists(path) or not os.path.isdir(path):  # Check if path exists and is directory
            self.log.error(f"Metadata catalog path does not exist or is not a directory: {path}")
            self.meta_df = pd.DataFrame()  # Create empty DataFrame if path invalid
            return

        # Find all parquet files in the metadata directory
        meta_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".parquet")]  # Get all parquet files
        if not meta_files:  # Check if any parquet files found
            self.log.warn(f"No .parquet files found in metadata catalog: {path}")
            self.meta_df = pd.DataFrame()  # Create empty DataFrame if no files
            return

        # Load and concatenate all metadata files
        self.log.info(f"Loading metadata from {len(meta_files)} file(s)...")  # Log loading progress
        self.meta_df = pd.concat((pd.read_parquet(f) for f in meta_files), ignore_index=True)  # Load all parquet files

        # Set up multi-index for fast lookups
        if not self.meta_df.empty and "instrument_id" in self.meta_df.columns and "timestamp" in self.meta_df.columns:  # Check required columns exist
            self.meta_df.set_index(["instrument_id", "timestamp"], inplace=True)  # Set multi-index for fast lookups
            self.meta_df.sort_index(inplace=True)  # Sort by index for efficient access
            self.log.info(f"Loaded {len(self.meta_df)} metadata records.")  # Log successful load
        else:
            self.log.error("Metadata DataFrame is missing 'instrument_id' or 'timestamp' columns.")  # Log error if columns missing
            self.meta_df = pd.DataFrame()  # Create empty DataFrame

    def _validate_quote_tick(self, tick: QuoteTick) -> tuple[bool, float, float]:
        """
        Validate quote tick prices and return safe bid/ask values.
        
        This method checks if the quote tick has valid bid and ask prices,
        filters out ticks with zero or negative prices, and validates
        the bid/ask spread for reasonableness.
        
        Args:
            tick: Quote tick to validate
            
        Returns:
            tuple: (is_valid, bid_price, ask_price)
                - is_valid: Boolean indicating if tick should be processed
                - bid_price: Validated bid price (float)
                - ask_price: Validated ask price (float)
        """
        bid_price = float(tick.bid_price)
        ask_price = float(tick.ask_price)
        
        # Check for zero or negative prices
        if bid_price <= 0 or ask_price <= 0:
            self.log.debug(f"Invalid prices detected - bid: {bid_price}, ask: {ask_price}")
            return False, bid_price, ask_price
        
        # Check for unreasonable bid/ask spread
        if bid_price > 0:  # Avoid division by zero
            spread_pct = (ask_price - bid_price) / bid_price * 100
            if spread_pct > 50:  # Skip if spread is more than 50%
                self.log.debug(f"Unreasonable spread detected - bid: {bid_price}, ask: {ask_price}, spread: {spread_pct:.2f}%")
                return False, bid_price, ask_price
        
        # Check for price sanity (options shouldn't be extremely expensive)
        if bid_price > 10000 or ask_price > 10000:
            self.log.debug(f"Extremely high prices detected - bid: {bid_price}, ask: {ask_price}")
            return False, bid_price, ask_price
        
        return True, bid_price, ask_price

    def on_start(self):
        """
        Called when the strategy starts.
        
        This method is called once when the strategy begins execution.
        It sets up the initial state and subscribes to quote ticks for
        the target instrument.
        """
        self.log.info("=== STRATEGY ON_START CALLED ===")  # Log strategy start
        
        # Subscribe to quote ticks for the target instrument
        self.subscribe_quote_ticks(self.config.instrument_id)  # Subscribe to market data
        
        self.log.info(f"Strategy started for instrument: {self.config.instrument_id}")  # Log instrument subscription
        self.log.info("=== STRATEGY ON_START COMPLETED ===")  # Log strategy start completion

    def on_quote_tick(self, tick: QuoteTick):
        """
        Handle quote tick events for market data processing.
        
        This method processes incoming quote ticks to detect trading opportunities
        and manage existing positions. It implements the core breakout logic with
        multiple filters for signal quality.
        
        Args:
            tick: Quote tick containing bid/ask prices and market data
        """
        # Only process ticks for the target instrument
        if tick.instrument_id != self.config.instrument_id:
            return
            
        self.log.info(f"=== RECEIVED QUOTE TICK: {tick} ===")  # Log received tick
        
        # VALIDATE BID/ASK PRICES - Handle zero or invalid prices
        is_valid, bid_price, ask_price = self._validate_quote_tick(tick)
        if not is_valid:
            self.log.info(f"Skipping tick with invalid prices - bid: {bid_price}, ask: {ask_price}")
            return
        
        # Get metadata for IV/OI filtering
        try:
            meta = self.meta_df.loc[(str(tick.instrument_id), tick.ts_event)]  # Get metadata for this tick
        except (KeyError, AttributeError):
            meta = {}  # Empty dict if metadata not found

        # Extract implied volatility and open interest from metadata
        iv = meta.get("impliedVolatility", 0)  # Get implied volatility
        oi = meta.get("openInterest", 0)  # Get open interest

        # Calculate mid price from bid/ask (now safe since we validated prices)
        price = (bid_price + ask_price) / 2  # Mid price calculation
        tick_time = pd.Timestamp(tick.ts_event, unit='ns').time()  # Convert timestamp to time
        eod_squareoff_time = time(hour=15, minute=20)  # End-of-day square-off time

        # Warm-up: wait until we have enough data points for analysis
        if len(self.rolling_last) < self.config.lookback_intervals:  # Check if enough data for analysis
            self.rolling_last.append(price)  # Add current price to rolling window
            self.log.info(f"Warming up - rolling window size: {len(self.rolling_last)}/{self.config.lookback_intervals}")  # DIAGNOSTIC
            return  # Exit early if not enough data

        # Calculate breakout levels from rolling window
        prev_top = max(self.rolling_last)      # Highest price in lookback window
        prev_bottom = min(self.rolling_last)   # Lowest price in lookback window
        
        # Entry trigger: price breaks above previous high with buffer
        entry_trigger = price > prev_top * (1 + self.config.entry_buffer_pct / 100)  # Check for breakout with buffer

        # Convert metadata to float values for filtering
        iv_f = float(iv) if iv not in (None, "", "nan") else 0  # Convert IV to float
        oi_change_f = float(oi) if oi else 0  # Convert OI to float

        # Skip entry logic if already in a trade
        if self.in_trade:  # Check if already in position
            self.log.info(f"Already in trade, skipping entry logic. Position: {self.position}")  # Log skip reason
        else:
            # Apply market filters
            buy_pressure = meta.get('totalBuyQuantity', 0) > meta.get('totalSellQuantity', 0)  # Check buy vs sell pressure
            iv_ok = iv_f >= self.config.min_iv                    # Implied volatility filter
            oi_ok = oi_change_f >= self.config.min_oi_change      # Open interest filter

            # DIAGNOSTIC: Log entry condition values
            self.log.info(f"DIAGNOSTIC - Entry conditions: price={price:.2f}, prev_top={prev_top:.2f}, entry_trigger={entry_trigger}, iv_f={iv_f:.4f}, iv_ok={iv_ok}, oi_change_f={oi_change_f}, oi_ok={oi_ok}")
            self.log.info(f"DIAGNOSTIC - Config values: min_iv={self.config.min_iv}, min_oi_change={self.config.min_oi_change}, entry_buffer_pct={self.config.entry_buffer_pct}")

            # ENTRY LOGIC
            if entry_trigger and iv_ok and oi_ok:  # Check all entry conditions
                self.log.info(f"*** ENTRY TRIGGERED! *** Price: {price:.2f}, IV: {iv_f:.4f}, OI: {oi_change_f}")  # Log entry trigger
                
                try:
                    # Create market order for entry
                    order = self.order_factory.market(  # Create market order
                        instrument_id=self.config.instrument_id,  # Target instrument
                        order_side=OrderSide.BUY,  # Buy order
                        quantity=Quantity.from_int(self.config.position_size),  # Position size
                        time_in_force=TimeInForce.DAY,  # Day order
                        reduce_only=False,  # Allow new position
                        quote_quantity=False,  # Use quantity not quote amount
                        tags=[f"entry-long-{self.order_count}"]  # Order tag for tracking
                    )
                    
                    # Submit the order
                    self.submit_order(order)  # Submit order to exchange
                    self.order_count += 1  # Increment order counter
                    self.log.info(f"Market order submitted successfully: {order}")  # Log order submission

                    # Set position parameters
                    self.entry_price = price  # Set entry price
                    self.sl_price = prev_bottom                    # Stop-loss at rolling window low
                    self.tp_price = price * (1 + self.config.tp_pct / 100)  # Take-profit at percentage
                    self.position_open_time = tick.ts_event  # Set position open time
                    self.breakeven_triggered = False  # Reset breakeven flag
                    self.direction = "long"  # Set position direction
                    
                    # Track current trade details
                    self.current_trade = {  # Initialize trade tracking
                        "entry_time": tick.ts_event,  # Entry timestamp
                        "entry_price": price,  # Entry price
                        "iv": iv_f,  # Implied volatility at entry
                        "oi_change": oi_change_f,  # Open interest change at entry
                        "entry_reason": "breakout"  # Entry reason
                    }
                    
                    self.log.info(f"Trade parameters set - Entry: {price:.2f}, SL: {self.sl_price:.2f}, TP: {self.tp_price:.2f}")  # Log trade setup

                except Exception as e:
                    self.log.error(f"ERROR creating/submitting order: {e}")  # Log order error
                    return  # Exit on error
            else:
                # DIAGNOSTIC: Log why entry was not triggered
                if not entry_trigger:
                    self.log.info(f"Entry not triggered: price {price:.2f} <= prev_top {prev_top:.2f} * (1 + {self.config.entry_buffer_pct/100:.4f}) = {prev_top * (1 + self.config.entry_buffer_pct / 100):.2f}")
                if not iv_ok:
                    self.log.info(f"IV filter failed: {iv_f:.4f} < {self.config.min_iv}")
                if not oi_ok:
                    self.log.info(f"OI filter failed: {oi_change_f} < {self.config.min_oi_change}")

        # EXIT LOGIC - Only process if we have a position
        if self.in_trade and self.direction == "long":  # Check if in long position
            
            # Stop-loss check
            if price <= self.sl_price:  # Check if stop-loss hit
                self.log.info(f"*** STOP LOSS HIT! *** Price: {price:.2f}, SL: {self.sl_price:.2f}")  # Log stop-loss
                self._exit_position("SL", price, tick.ts_event)  # Exit position
                return  # Exit early
                
            # Take-profit check
            elif price >= self.tp_price:  # Check if take-profit hit
                self.log.info(f"*** TAKE PROFIT HIT! *** Price: {price:.2f}, TP: {self.tp_price:.2f}")  # Log take-profit
                self._exit_position("TP", price, tick.ts_event)  # Exit position
                return  # Exit early
                
            # Breakeven trigger check
            elif not self.breakeven_triggered and price >= self.entry_price * (1 + self.config.breakeven_trigger_pct / 100):  # Check breakeven condition
                self.sl_price = self.entry_price  # Move stop-loss to entry price
                self.breakeven_triggered = True  # Set breakeven flag
                self.log.info(f"Breakeven triggered - SL moved to entry price: {self.entry_price:.2f}")  # Log breakeven
                
            # Trailing stop-loss update
            elif prev_bottom > self.sl_price:  # Check if new low is higher than current stop-loss
                old_sl = self.sl_price  # Store old stop-loss
                self.sl_price = prev_bottom  # Update to new low
                self.log.info(f"Trailing stop updated - SL: {old_sl:.2f} -> {self.sl_price:.2f}")  # Log trailing stop update

        # End-of-Day forced exit
        if tick_time >= eod_squareoff_time and self.in_trade and self.direction == "long":  # Check end-of-day condition
            self.log.info(f"*** EOD SQUAREOFF! *** Time: {tick_time}")  # Log end-of-day exit
            self._exit_position("EOD", price, tick.ts_event)  # Force exit position

        # Update rolling window with current price
        self.rolling_last.append(price)  # Add current price to rolling window
        if len(self.rolling_last) > self.config.lookback_intervals:  # Check if window is full
            self.rolling_last.popleft()  # Remove oldest price

    def _exit_position(self, reason, price, timestamp):
        """
        Helper method to exit a position.
        
        This method creates and submits a market order to close the current position.
        It updates trade tracking and resets position state.
        
        Args:
            reason: Exit reason (SL, TP, EOD, etc.)
            price: Current market price at exit
            timestamp: Exit timestamp
        """
        try:
            # Create market order to exit position
            order = self.order_factory.market(  # Create market exit order
                instrument_id=self.config.instrument_id,  # Target instrument
                order_side=OrderSide.SELL,  # Sell order to exit
                quantity=Quantity.from_int(self.config.position_size),  # Position size
                time_in_force=TimeInForce.DAY,  # Day order
                reduce_only=True,  # Only reduce position, don't create new one
                quote_quantity=False,  # Use quantity not quote amount
                tags=[f"exit-{reason.lower()}-{self.order_count}"]  # Order tag for tracking
            )
            
            # Submit the exit order
            self.submit_order(order)  # Submit exit order
            self.order_count += 1  # Increment order counter
            self.log.info(f"Exit order submitted: {order}")  # Log exit order

            # Update current trade with exit information
            if self.current_trade:  # Check if trade is being tracked
                self.current_trade.update({  # Update trade details
                    "exit_time": timestamp,  # Exit timestamp
                    "exit_price": price,  # Exit price
                    "exit_reason": reason,  # Exit reason
                    "pnl": (price - self.entry_price) * self.config.position_size if self.direction == "long" else (self.entry_price - price) * self.config.position_size  # Calculate P&L
                })
                
                # Add completed trade to trades list
                self.trades.append(self.current_trade)  # Add to completed trades
                self.log.info(f"Trade completed: {self.current_trade}")  # Log trade completion

        except Exception as e:
            self.log.error(f"ERROR creating/submitting exit order: {e}")  # Log exit order error

    def on_event(self, event: Event):
        """
        Handle trading events from the exchange.
        
        This method processes various trading events such as order fills,
        position updates, and other market events. It updates the strategy's
        internal state based on these events.
        
        Args:
            event: Trading event from the exchange
        """
        self.log.info(f"=== RECEIVED EVENT: {event} ===")  # Log received event
        
        # Handle position opened events
        if isinstance(event, PositionOpened):  # Check if position opened event
            self.position = self.cache.position(event.position_id)  # Get position object
            self.in_trade = True  # Set in-trade flag
            self.log.info(f"Position opened: {self.position}")  # Log position opening
            
        # Handle position closed events
        elif isinstance(event, PositionClosed):  # Check if position closed event
            self.log.info(f"Position closed: {event}")  # Log position closure
            self._reset_position()  # Reset position state for next trade
            
        # Handle order filled events
        elif isinstance(event, OrderFilled):  # Check if order filled event
            self.log.info(f"Order filled: {event}")  # Log order fill event
            
            # Only set in_trade=True if this is a position-opening order (not reduce_only)
            if hasattr(event, 'reduce_only') and not event.reduce_only:
                self.in_trade = True  # Set in-trade flag for position-opening orders
            
            # Update active orders - use client_order_id from event
            if event.client_order_id in self.active_orders:  # Check if order in active orders
                del self.active_orders[event.client_order_id]  # Remove from active orders

    def _reset_position(self):
        """
        Reset position state after position closure.
        
        This method clears all position-related variables and prepares
        the strategy for the next trading opportunity.
        """
        self.in_trade = False  # Reset in-trade flag
        self.position = None  # Clear position object
        self.entry_price = None  # Clear entry price
        self.sl_price = None  # Clear stop-loss price
        self.tp_price = None  # Clear take-profit price
        self.position_open_time = None  # Clear position open time
        self.breakeven_triggered = False  # Reset breakeven flag
        self.direction = None  # Clear position direction
        self.current_trade = None  # Clear current trade
        self.log.info("Position state reset - ready for next trade")  # Log position reset

    def on_stop(self):
        """
        Called when the strategy stops.
        
        This method is called when the strategy execution ends.
        It performs cleanup and final logging.
        """
        self.log.info("=== STRATEGY ON_STOP CALLED ===")  # Log strategy stop
        self.log.info(f"Strategy completed. Total trades: {len(self.trades)}")  # Log total trades
        
        # Log final statistics
        if self.trades:  # Check if any trades completed
            total_pnl = sum(trade.get('pnl', 0) for trade in self.trades)  # Calculate total P&L
            self.log.info(f"Total P&L: {total_pnl:.2f}")  # Log total P&L
            
        self.log.info("=== STRATEGY ON_STOP COMPLETED ===")  # Log strategy stop completion
