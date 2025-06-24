#!/usr/bin/env python3
"""
Engine Manager for MyNSEStrategy Backtesting

Handles backtest engine setup, configuration, and execution.
"""

from typing import Dict, Any
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import Venue, InstrumentId
from nautilus_trader.model.currencies import INR
from nautilus_trader.model.enums import OmsType, AccountType, BookType
from nautilus_trader.model.objects import Money
from strategies.my_nse_strategy.strategy import MyNSEStrategy
from nautilus_trader.config import LoggingConfig
import pandas as pd


class EngineManager:
    """Manages backtest engine setup and execution."""
    
    def __init__(self, trader_id: str = "BACKTESTER-001"):
        self.trader_id = trader_id
        self.engine = None
    
    def create_engine(self, verbose: bool = False) -> BacktestEngine:
        """Create and configure backtest engine."""
        log_level = "INFO" if verbose else "WARNING"
        logging_config = LoggingConfig(
            log_level=log_level,  # Console log level matches runner verbosity
            log_level_file="INFO",  # Optional: more details to file
        )
        self.engine = BacktestEngine(
            config=BacktestEngineConfig(
                trader_id=self.trader_id,
                logging=logging_config,
            ),
        )
        return self.engine
    
    def setup_venue(self, engine: BacktestEngine, 
                   venue_name: str = "NSE",
                   starting_balance: float = 1_000_000) -> None:
        """Setup trading venue with account."""
        engine.add_venue(
            venue=Venue(venue_name),
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            starting_balances=[Money(starting_balance, INR)],
            base_currency=INR,
            book_type=BookType.L1_MBP,
        )
    
    def add_instrument(self, engine: BacktestEngine, instrument) -> None:
        """Add instrument to engine."""
        engine.add_instrument(instrument)
    
    def add_data(self, engine: BacktestEngine, data) -> None:
        """Add data to engine."""
        engine.add_data(data)
    
    def add_strategy(self, engine: BacktestEngine, strategy: MyNSEStrategy) -> None:
        """Add strategy to engine."""
        engine.add_strategy(strategy)
    
    def run_backtest(self, engine: BacktestEngine) -> None:
        """Run the backtest."""
        engine.run()
    
    def get_results(self, engine: BacktestEngine):
        """Get backtest results and always attach account_balances and PnL fields to the result object."""
        result = engine.get_result()
        # Attach account_balances if available from engine
        if hasattr(engine, "account_balances") and engine.account_balances is not None:
            result.account_balances = engine.account_balances
        elif hasattr(engine, "cache") and hasattr(engine.cache, "accounts"):
            accounts = engine.cache.accounts()
            if accounts:
                data = []
                for acc in accounts:
                    total = acc.balance_total() if callable(getattr(acc, "balance_total", None)) else float(getattr(acc, "balance_total", 0.0))
                    data.append({
                        "venue": getattr(acc, "venue", "N/A"),
                        "currency": getattr(acc, "base_currency", "N/A"),
                        "total": float(total),
                    })
                result.account_balances = pd.DataFrame(data)
            else:
                result.account_balances = pd.DataFrame([])
        else:
            result.account_balances = None
        # Attach realized/unrealized/total PnL from portfolio if available
        try:
            portfolio = getattr(engine, 'portfolio', None)
            instrument_id = None
            # Try to get instrument_id from result if possible
            if hasattr(result, 'instrument_id'):
                instrument_id = getattr(result, 'instrument_id')
            elif hasattr(engine, 'instruments') and engine.instruments:
                instrument_id = list(engine.instruments.keys())[0]
            # Ensure instrument_id is InstrumentId object
            if instrument_id and not isinstance(instrument_id, InstrumentId):
                try:
                    instrument_id_obj = InstrumentId.from_str(str(instrument_id))
                except Exception:
                    instrument_id_obj = instrument_id
            else:
                instrument_id_obj = instrument_id
            # print(f"[DEBUG] Using instrument_id for portfolio: {instrument_id_obj} (type: {type(instrument_id_obj)})")
            if portfolio and instrument_id_obj:
                realized = portfolio.realized_pnl(instrument_id_obj)
                unrealized = portfolio.unrealized_pnl(instrument_id_obj)
                total = portfolio.total_pnl(instrument_id_obj)
                # print(f"[DEBUG] Portfolio PnL for {instrument_id_obj}: realized={realized}, unrealized={unrealized}, total={total}")
                result.realized_pnl = float(realized) if realized is not None else None
                result.unrealized_pnl = float(unrealized) if unrealized is not None else None
                result.total_pnl = float(total) if total is not None else None
                # Fallback: if realized_pnl is zero but there are closed positions with nonzero realized_pnl, sum those
                if abs(result.realized_pnl) < 1e-8 and hasattr(engine, 'trader'):
                    try:
                        positions_report = engine.trader.generate_positions_report()
                        realized_sum = 0.0
                        for _, row in positions_report.iterrows():
                            if str(row.get('side', '')).upper() == 'FLAT':
                                val = str(row.get('realized_pnl', '0.0')).replace('INR', '').replace('₹', '').replace(',', '').strip()
                                try:
                                    realized_sum += float(val)
                                except Exception:
                                    pass
                        # print(f"[DEBUG] Fallback sum of closed positions' realized_pnl: {realized_sum}")
                        result.realized_pnl = realized_sum
                    except Exception as e:
                        # print(f"[WARNING] Fallback realized_pnl extraction failed: {e}")
                        pass
        except Exception as e:
            # print(f"[WARNING] Failed to extract realized/unrealized/total PnL from portfolio: {e}")
            pass
        return result
    
    def cleanup(self) -> None:
        """Cleanup engine resources."""
        if self.engine:
            self.engine = None 