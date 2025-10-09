"""Single instrument backtest runner for ND_TT_V4 strategy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from strategies.nd_tt_v4.strategy import NdTtV4Strategy
from strategies.nd_tt_v4.config import NdTtV4Config
from utils.runners.engine_manager import EngineManager
from utils.data.data_manager import DataManager


class NdTtV4BacktestRunner:  # pylint: disable=too-few-public-methods
    """Execute ND_TT_V4 strategy for single instrument."""

    def __init__(self, prices_provider=None):
        self._prices_provider = prices_provider or self._load_prices

    def run(self, instrument_id: str) -> Dict[str, Any]:  # noqa: D401
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
        
        # Get catalog path from environment or use default
        import os
        catalog_path = os.environ.get("DATA_CATALOG_ROOTS", "catalog-data/nifty-2023/catalog")
        data_mgr = DataManager(catalog_path=catalog_path)
        
        # Override the broken get_all_instrument_ids method
        def get_nifty_instruments():
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog(catalog_path)
            return [str(inst.id) for inst in catalog.instruments()]
        
        data_mgr.get_all_instrument_ids = get_nifty_instruments

        engine = engine_mgr.create_engine()
        engine_mgr.setup_venue(engine)

        # Get instrument directly from catalog to bypass DataManager issues
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog(catalog_path)
            instruments = catalog.instruments(instrument_ids=[instrument_id])
            if instruments:
                instrument = instruments[0]
            else:
                # Create a dummy instrument for compatibility
                instrument = {"id": instrument_id}
        except Exception:
            instrument = {"id": instrument_id}
        engine_mgr.add_instrument(engine, instrument)

        prices = self._prices_provider(instrument_id)
        engine_mgr.add_data(engine, prices)
        engine_mgr.add_strategy(engine, strategy)
        
        # Run strategy directly (bypass EngineManager issues)
        for bar in prices:
            strategy.on_bar(bar)
        
        # Still get metrics from EngineManager for consistency
        result = engine_mgr.get_results(engine)
        
        # Inject strategy trades with proper date and OI formatting
        strategy_trades = []
        if hasattr(strategy, 'trades') and strategy.trades:
            for trade in strategy.trades:
                strategy_trades.append({
                    "Instrument": instrument_id,
                    "Entry_Date": trade.get("entry_date", "N/A"),
                    "Trade_Type": "Long" if trade.get("side") == "LONG" else "Short",
                    "Entry_Reason": trade.get("entry_reason", "N/A"),  # Add entry reason
                    "Exit_Reason": trade.get("exit_reason", trade.get("reason", "N/A")),  # Use exit_reason
                    "Entry_Price": trade.get("entry_price", 0.0),
                    "IV": 0.0,  # Not available in this dataset
                    "Entry_OI": trade.get("entry_oi", 0),
                    "Exit_Date": trade.get("exit_date", "N/A"),
                    "Exit_Price": trade.get("exit_price", 0.0),
                    "Exit_OI": trade.get("exit_oi", 0),
                    "Threshold": None,
                    "SL_Price": None,
                    "Realised_PnL": trade.get("pnl", 0.0),
                    "PnL%": (trade.get("pnl", 0.0) / trade.get("entry_price", 1.0)) * 100 if trade.get("entry_price") else 0.0,
                    "MDD_pct": result.get("mdd_pct", 0.0),
                    "Sharpe": result.get("sharpe", 0.0),
                    "Cum_PnL": None,
                })
        
        # Replace the fallback trades with our actual strategy trades
        if strategy_trades:
            result["trades"] = strategy_trades
            
            # Recalculate instrument-level PnL from actual trades (not equity curve)
            # This ensures the PnL accounts for contract multiplier
            total_pnl = sum(t.get("Realised_PnL", 0.0) for t in strategy_trades)
            result["pnl"] = total_pnl
            
            # Also recalculate return percentage based on actual PnL
            if hasattr(strategy, 'config') and strategy.config.initial_capital > 0:
                result["return_pct"] = (total_pnl / strategy.config.initial_capital) * 100
        
        # Ensure result has required fields for reporting
        result["instrument_id"] = instrument_id
        result["strategy_name"] = "nd_tt_v4"
        
        return result

    def _load_prices(self, instrument_id: str):  # noqa: D401
        """Load bars directly from Nautilus catalog to bypass DataManager issues."""
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            import os
            from pathlib import Path
            
            # Get catalog path from environment or use default
            catalog_path = os.environ.get("DATA_CATALOG_ROOTS", "catalog-data/nifty-2023/catalog")
            catalog = ParquetDataCatalog(catalog_path)
            
            # Auto-detect bar interval from catalog instead of environment variable
            # Look for available bar types in the catalog for this instrument
            bar_dir = Path(catalog_path) / "data" / "bar"
            available_bar_types = []
            if bar_dir.exists():
                for bar_type_dir in bar_dir.iterdir():
                    if bar_type_dir.is_dir() and instrument_id in bar_type_dir.name:
                        available_bar_types.append(bar_type_dir.name)
            
            if not available_bar_types:
                raise ValueError(f"No bar types found for {instrument_id} in catalog")
            
            # Use the first available bar type (should only be one per instrument)
            bar_type = available_bar_types[0]
            print(f"Loading bar type: {bar_type}")
            bars = catalog.bars(bar_types=[bar_type], as_nautilus=False)
            
            if not bars:
                raise ValueError(f"No bars found for {bar_type}")
                
            # Return actual bar objects with timestamps, not just prices
            print(f"Loaded {len(bars)} bars for {instrument_id}")
            closes = [float(bar.close) for bar in bars]
            print(f"Price range: {min(closes):.2f} to {max(closes):.2f}")
            
            # Load OI metadata if available
            oi_by_timestamp = {}
            try:
                import pandas as pd
                meta_path_base = catalog_path.replace("/catalog", "/catalog-meta")
                meta_file = Path(meta_path_base) / "bar_metadata.parquet"
                if meta_file.exists():
                    meta_df = pd.read_parquet(meta_file)
                    # Filter for this instrument
                    inst_meta = meta_df[meta_df['instrument_id'] == instrument_id]
                    if not inst_meta.empty and 'OI' in inst_meta.columns:
                        oi_by_timestamp = dict(zip(inst_meta['timestamp'], inst_meta['OI']))
                        print(f"Loaded OI metadata for {len(oi_by_timestamp)} bars")
            except Exception as e:
                print(f"Could not load OI metadata: {e}")
            
            # Extract bar interval from bar_type for date formatting
            # bar_type format: "INSTRUMENT-NUMBER-UNIT-AGGREGATION-SOURCE"
            # e.g., "NIFTY20240229.FUT.NSE-1-HOUR-LAST-EXTERNAL"
            parts = bar_type.split('-')
            if len(parts) >= 3:
                bar_interval = f"{parts[-4]}-{parts[-3]}"  # e.g., "1-HOUR" or "1-DAY"
            else:
                bar_interval = '1-DAY'
            
            # Create enriched bars with date and OI information
            from datetime import datetime
            enriched_bars = []
            for i, bar in enumerate(bars):
                class EnrichedBar:
                    def __init__(self, nautilus_bar, date_str, oi_val):
                        self._bar = nautilus_bar
                        self.date_str = date_str
                        self.oi = oi_val
                        # Expose all bar attributes
                        for attr in ['open', 'high', 'low', 'close', 'volume', 'ts_event', 'ts_init']:
                            if hasattr(nautilus_bar, attr):
                                setattr(self, attr, getattr(nautilus_bar, attr))
                
                if hasattr(bar, 'ts_event'):
                    # Format timestamp based on bar interval
                    # Show time only for intraday data (HOUR, MINUTE, SECOND)
                    if any(unit in bar_interval for unit in ['HOUR', 'MINUTE', 'SECOND']):
                        date_str = datetime.fromtimestamp(bar.ts_event / 1_000_000_000).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        # Daily or higher - show date only
                        date_str = datetime.fromtimestamp(bar.ts_event / 1_000_000_000).strftime('%Y-%m-%d')
                else:
                    date_str = f"2023-{6+i//30:02d}-{(i%30)+1:02d}"  # Synthetic date
                
                # Get OI for this bar
                oi_val = oi_by_timestamp.get(bar.ts_event, 0) if hasattr(bar, 'ts_event') else 0
                
                enriched_bars.append(EnrichedBar(bar, date_str, oi_val))
            
            return enriched_bars
            
        except Exception as e:
            print(f"FAILED to load real data for {instrument_id}: {e}")
            raise ValueError(f"No real data found for instrument {instrument_id}. Check catalog.")

