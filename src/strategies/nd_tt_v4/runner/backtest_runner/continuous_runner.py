"""Single instrument backtest runner for ND_TT_V4 strategy with continuous futures support.

This runner extends the base runner with:
- Support for continuous futures contracts
- Date range filtering (start_date, end_date)
- Flexible catalog path configuration
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from strategies.nd_tt_v4.strategy import NdTtV4Strategy
from strategies.nd_tt_v4.config import NdTtV4Config
from utils.runners.engine_manager import EngineManager
from utils.data.data_manager import DataManager


class NdTtV4ContinuousBacktestRunner:
    """Execute ND_TT_V4 strategy for continuous futures with date filtering."""

    def __init__(
        self,
        catalog_path: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bar_interval: str = "1-DAY",
        prices_provider=None,
    ):
        """Initialize runner with optional date range and catalog path.
        
        Args:
            catalog_path: Path to Nautilus catalog (default: from env or config)
            start_date: Start date for backtest (YYYY-MM-DD format)
            end_date: End date for backtest (YYYY-MM-DD format)
            bar_interval: Bar interval (e.g., '1-DAY', '1-HOUR', '5-MINUTE')
            prices_provider: Optional custom price provider
        """
        self._catalog_path = catalog_path or os.environ.get(
            "DATA_CATALOG_ROOTS", "catalog-data/nifty-continuous-yf/catalog"
        )
        self._start_date = start_date
        self._end_date = end_date
        self._bar_interval = bar_interval
        self._prices_provider = prices_provider or self._load_prices

    def run(self, instrument_id: str) -> Dict[str, Any]:
        """Run backtest for a single instrument.
        
        Args:
            instrument_id: Instrument identifier (e.g., NIFTY_CONTINUOUS.FUT.NSE)
            
        Returns:
            Dictionary with backtest results including trades and metrics
        """
        # Load strategy configuration
        cfg_path = Path(__file__).resolve().parents[2] / "strategy.yaml"
        if cfg_path.exists():
            config = NdTtV4Config.from_yaml(str(cfg_path), instrument_id=instrument_id)
        else:
            config = NdTtV4Config(instrument_id=instrument_id)

        strategy = NdTtV4Strategy(config)

        # Force stub engine to ensure our strategy gets called
        import utils.runners.engine_manager as em
        original_nautilus_available = em.NAUTILUS_AVAILABLE
        em.NAUTILUS_AVAILABLE = False  # Force stub engine
        
        engine_mgr = EngineManager()
        
        # Restore original value
        em.NAUTILUS_AVAILABLE = original_nautilus_available
        
        # Set catalog path
        os.environ["DATA_CATALOG_ROOTS"] = self._catalog_path
        data_mgr = DataManager(catalog_path=self._catalog_path)
        
        # Override get_all_instrument_ids for continuous contracts
        def get_continuous_instruments():
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog(self._catalog_path)
            return [str(inst.id) for inst in catalog.instruments()]
        
        data_mgr.get_all_instrument_ids = get_continuous_instruments

        engine = engine_mgr.create_engine()
        engine_mgr.setup_venue(engine)

        # Get instrument from catalog
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog(self._catalog_path)
            instruments = catalog.instruments(instrument_ids=[instrument_id])
            if instruments:
                instrument = instruments[0]
            else:
                instrument = {"id": instrument_id}
        except Exception:
            instrument = {"id": instrument_id}
        
        engine_mgr.add_instrument(engine, instrument)

        # Load prices with date filtering
        prices = self._prices_provider(instrument_id)
        prices = self._filter_by_date(prices)
        
        if not prices:
            raise ValueError(
                f"No price data found for {instrument_id} "
                f"between {self._start_date or 'start'} and {self._end_date or 'end'}"
            )
        
        print(f"Running backtest on {len(prices)} bars from {prices[0].date_str} to {prices[-1].date_str}")
        
        engine_mgr.add_data(engine, prices)
        engine_mgr.add_strategy(engine, strategy)
        
        # Run strategy directly (bypass EngineManager issues)
        for bar in prices:
            strategy.on_bar(bar)
        
        # Get metrics from EngineManager
        result = engine_mgr.get_results(engine)
        
        # Inject strategy trades with proper formatting
        strategy_trades = []
        if hasattr(strategy, 'trades') and strategy.trades:
            for trade in strategy.trades:
                strategy_trades.append({
                    "Instrument": instrument_id,
                    "Entry_Date": trade.get("entry_date", "N/A"),
                    "Trade_Type": "Long" if trade.get("side") == "LONG" else "Short",
                    "Exit_Reason": trade.get("reason", "N/A"),
                    "Entry_Price": trade.get("entry_price", 0.0),
                    "IV": 0.0,  # IV not applicable for futures
                    "OI": trade.get("entry_oi", 0),  # Use actual OI from entry
                    "Exit_Date": trade.get("exit_date", "N/A"),
                    "Exit_Price": trade.get("exit_price", 0.0),
                    "Exit_OI": trade.get("exit_oi", 0),  # Exit OI for analysis
                    "Threshold": None,
                    "SL_Price": None,
                    "Realised_PnL": trade.get("pnl", 0.0),
                    "PnL%": (trade.get("pnl", 0.0) / trade.get("entry_price", 1.0)) * 100 
                            if trade.get("entry_price") else 0.0,
                    "MDD_pct": result.get("mdd_pct", 0.0),
                    "Sharpe": result.get("sharpe", 0.0),
                    "Cum_PnL": None,
                })
        
        # Replace with actual strategy trades
        if strategy_trades:
            result["trades"] = strategy_trades
            
            # Recalculate metrics from actual trades
            total_pnl = sum(t.get("Realised_PnL", 0) for t in strategy_trades)
            wins = [t for t in strategy_trades if t.get("Realised_PnL", 0) > 0]
            losses = [t for t in strategy_trades if t.get("Realised_PnL", 0) < 0]
            
            result["total_pnl"] = total_pnl
            result["num_trades"] = len(strategy_trades)
            result["num_wins"] = len(wins)
            result["num_losses"] = len(losses)
            result["win_rate"] = len(wins) / len(strategy_trades) if strategy_trades else 0
            result["avg_win"] = sum(t["Realised_PnL"] for t in wins) / len(wins) if wins else 0
            result["avg_loss"] = sum(t["Realised_PnL"] for t in losses) / len(losses) if losses else 0
        
        # Add metadata
        result["instrument_id"] = instrument_id
        result["strategy_name"] = "nd_tt_v4"
        result["start_date"] = self._start_date or "N/A"
        result["end_date"] = self._end_date or "N/A"
        result["total_bars"] = len(prices)
        
        return result

    def _load_prices(self, instrument_id: str):
        """Load bars directly from Nautilus catalog."""
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog(self._catalog_path)
            
            # Load bars for this instrument with configured interval
            bar_type = f"{instrument_id}-{self._bar_interval}-LAST-EXTERNAL"
            bars = catalog.bars(bar_types=[bar_type], as_nautilus=False)
            
            if not bars:
                raise ValueError(f"No bars found for {bar_type}")
            
            print(f"Loaded {len(bars)} bars from catalog")
            
            # Load OI metadata if available
            oi_data = {}
            try:
                import pandas as pd
                from pathlib import Path
                catalog_base = Path(self._catalog_path).parent
                oi_meta_path = catalog_base / "catalog-meta" / "bar_metadata.parquet"
                if oi_meta_path.exists():
                    meta_df = pd.read_parquet(oi_meta_path)
                    for _, row in meta_df.iterrows():
                        ts = row.get('timestamp')
                        oi = row.get('OI', 0)
                        if ts and oi:
                            oi_data[ts] = oi
                    print(f"Loaded OI metadata for {len(oi_data)} bars")
            except Exception as e:
                print(f"Could not load OI metadata: {e}")
            
            # Create enriched bars with date and OI information
            enriched_bars = []
            for bar in bars:
                class EnrichedBar:
                    def __init__(self, nautilus_bar, date_str, oi_value=0):
                        self._bar = nautilus_bar
                        self.date_str = date_str
                        self.oi = oi_value
                        # Expose all bar attributes
                        for attr in ['open', 'high', 'low', 'close', 'volume', 'ts_event', 'ts_init']:
                            if hasattr(nautilus_bar, attr):
                                setattr(self, attr, getattr(nautilus_bar, attr))
                
                if hasattr(bar, 'ts_event'):
                    date_str = datetime.fromtimestamp(bar.ts_event / 1_000_000_000).strftime('%Y-%m-%d')
                    oi_value = oi_data.get(bar.ts_event, 0)
                else:
                    date_str = "N/A"
                    oi_value = 0
                
                enriched_bars.append(EnrichedBar(bar, date_str, oi_value))
            
            return enriched_bars
            
        except Exception as e:
            raise ValueError(f"Failed to load data for {instrument_id}: {e}") from e

    def _filter_by_date(self, bars):
        """Filter bars by start_date and end_date."""
        if not self._start_date and not self._end_date:
            return bars
        
        filtered = []
        for bar in bars:
            bar_date = bar.date_str
            
            # Skip if before start_date
            if self._start_date and bar_date < self._start_date:
                continue
            
            # Skip if after end_date
            if self._end_date and bar_date > self._end_date:
                continue
            
            filtered.append(bar)
        
        return filtered

