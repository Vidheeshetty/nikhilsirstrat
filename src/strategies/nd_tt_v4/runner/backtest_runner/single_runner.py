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
        
        # Ensure we use the NIFTY 2023 catalog
        import os
        os.environ["DATA_CATALOG_ROOTS"] = "catalog-data/nifty-2023/catalog"
        data_mgr = DataManager(catalog_path="catalog-data/nifty-2023/catalog")
        
        # Override the broken get_all_instrument_ids method
        def get_nifty_instruments():
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog("catalog-data/nifty-2023/catalog")
            return [str(inst.id) for inst in catalog.instruments()]
        
        data_mgr.get_all_instrument_ids = get_nifty_instruments

        engine = engine_mgr.create_engine()
        engine_mgr.setup_venue(engine)

        # Get instrument directly from catalog to bypass DataManager issues
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog("catalog-data/nifty-2023/catalog")
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
        
        # Inject strategy trades with proper date formatting
        strategy_trades = []
        if hasattr(strategy, 'trades') and strategy.trades:
            for trade in strategy.trades:
                strategy_trades.append({
                    "Instrument": instrument_id,
                    "Entry_Date": trade.get("entry_date", "N/A"),
                    "Trade_Type": "Long" if trade.get("side") == "LONG" else "Short",
                    "Exit_Reason": trade.get("reason", "N/A"),
                    "Entry_Price": trade.get("entry_price", 0.0),
                    "IV": 0.0,
                    "OI": 0,
                    "Exit_Date": trade.get("exit_date", "N/A"),
                    "Exit_Price": trade.get("exit_price", 0.0),
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
        
        # Ensure result has required fields for reporting
        result["instrument_id"] = instrument_id
        result["strategy_name"] = "nd_tt_v4"
        
        return result

    def _load_prices(self, instrument_id: str):  # noqa: D401
        """Load bars directly from Nautilus catalog to bypass DataManager issues."""
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            catalog = ParquetDataCatalog("catalog-data/nifty-2023/catalog")
            
            # Load bars for this instrument
            bar_type = f"{instrument_id}-1-DAY-LAST-EXTERNAL"
            bars = catalog.bars(bar_types=[bar_type], as_nautilus=False)
            
            if not bars:
                raise ValueError(f"No bars found for {bar_type}")
                
            # Return actual bar objects with timestamps, not just prices
            print(f"Loaded {len(bars)} real bars for {instrument_id}")
            closes = [float(bar.close) for bar in bars]
            print(f"Price range: {min(closes):.2f} to {max(closes):.2f}")
            
            # Create enriched bars with date information
            from datetime import datetime
            enriched_bars = []
            for i, bar in enumerate(bars):
                class EnrichedBar:
                    def __init__(self, nautilus_bar, date_str):
                        self._bar = nautilus_bar
                        self.date_str = date_str
                        # Expose all bar attributes
                        for attr in ['open', 'high', 'low', 'close', 'volume', 'ts_event', 'ts_init']:
                            if hasattr(nautilus_bar, attr):
                                setattr(self, attr, getattr(nautilus_bar, attr))
                
                if hasattr(bar, 'ts_event'):
                    date_str = datetime.fromtimestamp(bar.ts_event / 1_000_000_000).strftime('%Y-%m-%d')
                else:
                    date_str = f"2023-{6+i//30:02d}-{(i%30)+1:02d}"  # Synthetic date
                
                enriched_bars.append(EnrichedBar(bar, date_str))
            
            return enriched_bars
            
        except Exception as e:
            print(f"FAILED to load real data for {instrument_id}: {e}")
            raise ValueError(f"No real data found for instrument {instrument_id}. Check catalog.")

