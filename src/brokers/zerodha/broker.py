"""
Zerodha Broker Implementation

Integration with Zerodha KiteConnect API for paper trading and live trading.
This implementation supports live market data with virtual orders for paper trading.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import threading

from ..base import BaseBroker, Order, Position, Trade
from ..paper import PaperBroker
from .config import ZerodhaConfig

logger = logging.getLogger(__name__)


class ZerodhaBroker(BaseBroker):
    """
    Zerodha broker implementation.

    Supports both paper trading (virtual orders) and live trading.
    For paper trading, orders are virtual but market data is live from Zerodha WebSocket.
    """

    def __init__(self, config: ZerodhaConfig):
        """Initialize Zerodha broker."""
        super().__init__(config)
        self.zerodha_config = config
        
        # Always use PaperBroker for order management in paper trading mode
        if config.paper_trading:
            self._paper_broker = PaperBroker(config)
        else:
            # TODO: Implement live order management
            self._paper_broker = PaperBroker(config)
            logger.warning("Live order management not implemented yet, using paper broker")

        # Live data components (used even in paper trading)
        self._kite_client = None
        self._kite_ticker = None
        self._live_data_enabled = False
        self._subscribed_instruments = set()
        self._quote_callbacks = {}
        self._current_quotes = {}
        self._ticker_thread = None
        self._connected_to_live_data = False

    async def connect(self) -> bool:
        """Connect to Zerodha API."""
        # Connect paper broker for order management
        paper_connected = await self._paper_broker.connect()
        
        # Connect to live data if credentials are available
        live_data_connected = await self._connect_live_data()
        
        self._connected = paper_connected
        return paper_connected

    async def _connect_live_data(self) -> bool:
        """Connect to Zerodha live data feed."""
        try:
            # Only connect to live data if we have valid credentials
            if not self.zerodha_config.api_key or not self.zerodha_config.access_token:
                logger.info("No Zerodha credentials provided, live data disabled")
                return False
                
            # Import KiteConnect - this might fail if not installed
            try:
                from kiteconnect import KiteConnect, KiteTicker
            except ImportError:
                logger.warning("kiteconnect package not installed, live data disabled")
                return False

            # Initialize KiteConnect client
            self._kite_client = KiteConnect(api_key=self.zerodha_config.api_key)
            self._kite_client.set_access_token(self.zerodha_config.access_token)
            
            # Test connection
            try:
                profile = self._kite_client.profile()
                logger.info(f"Connected to Zerodha as: {profile.get('user_name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to authenticate with Zerodha: {e}")
                return False

            # Initialize WebSocket ticker
            self._kite_ticker = KiteTicker(
                api_key=self.zerodha_config.api_key,
                access_token=self.zerodha_config.access_token
            )
            
            # Set up WebSocket callbacks
            self._kite_ticker.on_connect = self._on_ws_connect
            self._kite_ticker.on_ticks = self._on_ws_ticks
            self._kite_ticker.on_error = self._on_ws_error
            self._kite_ticker.on_close = self._on_ws_close
            
            self._live_data_enabled = True
            logger.info("Zerodha live data connection initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Zerodha live data: {e}")
            return False

    def _on_ws_connect(self, ws, response):
        """WebSocket connection callback."""
        logger.info("Zerodha WebSocket connected")
        self._connected_to_live_data = True
        
        # Subscribe to any instruments that were requested before connection
        if self._subscribed_instruments:
            try:
                instrument_tokens = list(self._subscribed_instruments)
                ws.subscribe(instrument_tokens)
                ws.set_mode(ws.MODE_FULL, instrument_tokens)
                logger.info(f"Subscribed to {len(instrument_tokens)} instruments")
            except Exception as e:
                logger.error(f"Failed to subscribe to instruments: {e}")

    def _on_ws_ticks(self, ws, ticks):
        """WebSocket ticks callback."""
        for tick in ticks:
            try:
                instrument_token = tick.get('instrument_token')
                if not instrument_token:
                    continue
                    
                # Convert tick to our quote format
                quote = {
                    'instrument_token': instrument_token,
                    'last_price': tick.get('last_price', 0),
                    'bid': tick.get('depth', {}).get('buy', [{}])[0].get('price', 0),
                    'ask': tick.get('depth', {}).get('sell', [{}])[0].get('price', 0),
                    'volume': tick.get('volume', 0),
                    'oi': tick.get('oi', 0),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Store current quote
                self._current_quotes[instrument_token] = quote
                
                # Call registered callbacks
                for callback in self._quote_callbacks.get(instrument_token, []):
                    try:
                        callback(str(instrument_token), quote)
                    except Exception as e:
                        logger.error(f"Error in quote callback: {e}")
                        
            except Exception as e:
                logger.error(f"Error processing tick: {e}")

    def _on_ws_error(self, ws, code, reason):
        """WebSocket error callback."""
        logger.error(f"Zerodha WebSocket error {code}: {reason}")
        self._connected_to_live_data = False

    def _on_ws_close(self, ws, code, reason):
        """WebSocket close callback."""
        logger.warning(f"Zerodha WebSocket closed {code}: {reason}")
        self._connected_to_live_data = False

    def _start_websocket(self):
        """Start WebSocket in a separate thread."""
        if self._kite_ticker and not self._ticker_thread:
            self._ticker_thread = threading.Thread(
                target=self._kite_ticker.connect, 
                daemon=True
            )
            self._ticker_thread.start()
            logger.info("Zerodha WebSocket thread started")

    def _get_instrument_token(self, instrument_id: str) -> Optional[int]:
        """Get instrument token from instrument ID."""
        try:
            if not self._kite_client:
                return None
                
            # Parse instrument ID: CRUDEOIL20250721.FUT.MCX
            parts = instrument_id.split('.')
            if len(parts) < 3:
                logger.error(f"Invalid instrument ID format: {instrument_id}")
                return None
                
            symbol = parts[0]  # CRUDEOIL20250721
            exchange = parts[2]  # MCX
            
            # Get instruments for the exchange
            instruments = self._kite_client.instruments(exchange)
            
            # Find matching instrument
            for inst in instruments:
                if inst['tradingsymbol'] == symbol:
                    return inst['instrument_token']
                    
            logger.error(f"Instrument not found: {symbol} on {exchange}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting instrument token: {e}")
            return None

    async def disconnect(self) -> None:
        """Disconnect from Zerodha API."""
        # Disconnect paper broker
        if hasattr(self, "_paper_broker"):
            await self._paper_broker.disconnect()
            
        # Disconnect WebSocket
        if self._kite_ticker:
            try:
                self._kite_ticker.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
                
        self._connected_to_live_data = False
        self._connected = False
        logger.info("Zerodha broker disconnected")

    async def place_order(self, order: Order) -> str:
        """Place an order with Zerodha."""
        # Always use paper broker for orders in paper trading mode
        return await self._paper_broker.place_order(order)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return await self._paper_broker.cancel_order(order_id)

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ) -> bool:
        """Modify an existing order."""
        return await self._paper_broker.modify_order(order_id, quantity, price)

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get current status of an order."""
        return await self._paper_broker.get_order_status(order_id)

    async def get_orders(self) -> List[Order]:
        """Get all orders."""
        return await self._paper_broker.get_orders()

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        return await self._paper_broker.get_positions()

    async def get_position(self, instrument_id: str) -> Optional[Position]:
        """Get position for a specific instrument."""
        return await self._paper_broker.get_position(instrument_id)

    async def get_trades(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """Get trade history."""
        return await self._paper_broker.get_trades(start_date, end_date)

    async def get_quote(self, instrument_id: str) -> Dict[str, Any]:
        """Get current quote for an instrument."""
        if not self._live_data_enabled or not self._connected_to_live_data:
            # Fall back to paper broker simulation
            return await self._paper_broker.get_quote(instrument_id)
            
        try:
            # Get instrument token
            instrument_token = self._get_instrument_token(instrument_id)
            if not instrument_token:
                return await self._paper_broker.get_quote(instrument_id)
                
            # Return cached quote if available
            if instrument_token in self._current_quotes:
                quote = self._current_quotes[instrument_token].copy()
                quote['instrument_id'] = instrument_id
                return quote
                
            # If no cached quote, try to get it directly from API
            if self._kite_client:
                try:
                    kite_quote = self._kite_client.quote([instrument_id])
                    if instrument_id in kite_quote:
                        data = kite_quote[instrument_id]
                        return {
                            'instrument_id': instrument_id,
                            'last_price': data.get('last_price', 0),
                            'bid': data.get('depth', {}).get('buy', [{}])[0].get('price', 0),
                            'ask': data.get('depth', {}).get('sell', [{}])[0].get('price', 0),
                            'volume': data.get('volume', 0),
                            'oi': data.get('oi', 0),
                            'timestamp': datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.error(f"Error getting quote from API: {e}")
                    
            # Fall back to paper broker
            return await self._paper_broker.get_quote(instrument_id)
            
        except Exception as e:
            logger.error(f"Error in get_quote: {e}")
            return await self._paper_broker.get_quote(instrument_id)

    async def subscribe_quotes(
        self, instrument_ids: List[str], callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Subscribe to real-time quotes."""
        if not self._live_data_enabled:
            # Fall back to paper broker
            await self._paper_broker.subscribe_quotes(instrument_ids, callback)
            return
            
        try:
            # Get instrument tokens
            tokens_to_subscribe = []
            for instrument_id in instrument_ids:
                token = self._get_instrument_token(instrument_id)
                if token:
                    tokens_to_subscribe.append(token)
                    self._subscribed_instruments.add(token)
                    
                    # Register callback
                    if token not in self._quote_callbacks:
                        self._quote_callbacks[token] = []
                    self._quote_callbacks[token].append(callback)
                    
            if tokens_to_subscribe:
                # Start WebSocket if not already started
                if not self._ticker_thread:
                    self._start_websocket()
                    
                # Subscribe to instruments if WebSocket is connected
                if self._connected_to_live_data and self._kite_ticker:
                    try:
                        self._kite_ticker.subscribe(tokens_to_subscribe)
                        self._kite_ticker.set_mode(
                            self._kite_ticker.MODE_FULL, 
                            tokens_to_subscribe
                        )
                        logger.info(f"Subscribed to {len(tokens_to_subscribe)} instruments")
                    except Exception as e:
                        logger.error(f"Failed to subscribe to WebSocket: {e}")
                        
        except Exception as e:
            logger.error(f"Error in subscribe_quotes: {e}")
            # Fall back to paper broker
            await self._paper_broker.subscribe_quotes(instrument_ids, callback)

    async def unsubscribe_quotes(self, instrument_ids: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        if not self._live_data_enabled:
            await self._paper_broker.unsubscribe_quotes(instrument_ids)
            return
            
        try:
            tokens_to_unsubscribe = []
            for instrument_id in instrument_ids:
                token = self._get_instrument_token(instrument_id)
                if token and token in self._subscribed_instruments:
                    tokens_to_unsubscribe.append(token)
                    self._subscribed_instruments.discard(token)
                    
                    # Remove callbacks
                    if token in self._quote_callbacks:
                        del self._quote_callbacks[token]
                        
            if tokens_to_unsubscribe and self._kite_ticker:
                try:
                    self._kite_ticker.unsubscribe(tokens_to_unsubscribe)
                    logger.info(f"Unsubscribed from {len(tokens_to_unsubscribe)} instruments")
                except Exception as e:
                    logger.error(f"Failed to unsubscribe from WebSocket: {e}")
                    
        except Exception as e:
            logger.error(f"Error in unsubscribe_quotes: {e}")

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance and margins."""
        return await self._paper_broker.get_account_balance()

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get account holdings."""
        return await self._paper_broker.get_holdings()

    # Zerodha-specific methods

    def get_instrument_token(self, symbol: str) -> Optional[str]:
        """Get instrument token for a symbol."""
        token_map = self.zerodha_config.get_instrument_token_map()
        return token_map.get(symbol)

    def format_instrument_id(self, symbol: str, exchange: str = "NSE") -> str:
        """Format instrument ID for Zerodha."""
        return f"{symbol}.{exchange}"

    async def get_margins(self) -> Dict[str, Any]:
        """Get margin information."""
        balance = await self._paper_broker.get_account_balance()
        return {
            "available": balance.get("available_balance", 0),
            "used": balance.get("used_margin", 0),
            "total": balance.get("cash", 0),
        }

    def is_connected_to_live_data(self) -> bool:
        """Check if connected to live data feed."""
        return self._connected_to_live_data

    def get_live_data_status(self) -> Dict[str, Any]:
        """Get status of live data connection."""
        return {
            "enabled": self._live_data_enabled,
            "connected": self._connected_to_live_data,
            "subscribed_instruments": len(self._subscribed_instruments),
            "websocket_active": self._ticker_thread is not None and self._ticker_thread.is_alive() if self._ticker_thread else False
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check including live data connection status."""
        try:
            # Get base health check from paper broker
            base_health = await self._paper_broker.health_check()
            
            # Add live data connection status
            base_health["connected"] = self._connected_to_live_data
            
            return base_health
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": self._connected_to_live_data,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
