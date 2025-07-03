"""Historical data loader for SMA Fractal Scalper strategy warm-up."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Any

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Loads historical data from Parquet catalog for indicator warm-up."""

    def __init__(self, catalog_path: str = "catalog-data"):
        """Initialize the historical data loader.

        Args:
            catalog_path: Path to the Parquet data catalog
        """
        # For paper trading, use the correct catalog path
        if catalog_path == "catalog-data":
            # Check for CRUDEOIL data in the correct catalog structure
            # Container path: /workspace/catalog-data/source=Zerodha/...
            zerodha_crude_path = "catalog-data/source=Zerodha/instrument=FUT/venue=MCX/symbol=CRUDEOIL/timeframe=MIN/catalog"
            if Path(zerodha_crude_path).exists():
                catalog_path = zerodha_crude_path
                logger.info(f"Found CRUDEOIL catalog at: {catalog_path}")
            else:
                # Fallback to standard catalog-data directory
                catalog_path = "catalog-data"
                logger.info(f"Using fallback catalog path: {catalog_path}")

        self.catalog_path = catalog_path
        self._catalog = None
        logger.info(f"Historical loader initialized with catalog path: {catalog_path}")

    def _get_catalog(self):
        """Lazy load the catalog to avoid import issues."""
        if self._catalog is None:
            try:
                from nautilus_trader.persistence.catalog.parquet import (
                    ParquetDataCatalog,
                )

                self._catalog = ParquetDataCatalog(self.catalog_path)
                logger.info(f"Nautilus Trader catalog loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import Nautilus Trader: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to create Nautilus catalog: {e}")
                raise
        return self._catalog

    def load_recent_bars(
        self, instrument_id: str, num_bars: int = 100, bar_type: str = "1MIN"
    ) -> List[Any]:
        """Load recent historical bars for indicator warm-up.

        Args:
            instrument_id: The instrument ID to load data for
            num_bars: Number of recent bars to load (default: 100)
            bar_type: Bar type specification (default: "1MIN")

        Returns:
            List of bar objects with .open, .high, .low, .close attributes
        """
        try:
            catalog = self._get_catalog()

            # Calculate date range - go back enough days to get the required bars
            # For 1-minute bars, we need roughly num_bars/390 trading days (6.5 hours * 60 minutes)
            # Add some buffer for weekends and holidays
            end_date = datetime.now()
            days_back = max(5, (num_bars // 300) + 7)  # At least 5 days, with buffer
            start_date = end_date - timedelta(days=days_back)

            logger.info(f"Loading historical data for {instrument_id}")
            logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
            logger.info(f"Looking for {num_bars} recent {bar_type} bars")

            # Try to load bars from catalog using Nautilus Trader methods
            bars = catalog.bars(
                instrument_ids=[instrument_id],
                start=start_date,
                end=end_date,
                as_nautilus=True,
            )

            if not bars:
                logger.warning(f"No historical bars found for {instrument_id}")
                return []

            # Sort by timestamp (should already be sorted, but ensure)
            bars.sort(key=lambda b: b.ts_init)

            # Take the most recent num_bars
            recent_bars = bars[-num_bars:] if len(bars) > num_bars else bars

            logger.info(f"✅ Loaded {len(recent_bars)} historical bars for warm-up")
            if recent_bars:
                logger.info(
                    f"   Date range: {self._format_bar_time(recent_bars[0])} to {self._format_bar_time(recent_bars[-1])}"
                )

            return recent_bars

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            logger.info("Strategy will start without historical warm-up")
            return []

    def load_previous_day_bars(
        self, instrument_id: str, bar_type: str = "1MIN"
    ) -> List[Any]:
        """Load all bars from the previous trading day.

        Args:
            instrument_id: The instrument ID to load data for
            bar_type: Bar type specification (default: "1MIN")

        Returns:
            List of bar objects from previous trading day
        """
        try:
            catalog = self._get_catalog()

            # Get yesterday's date (previous trading day)
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            # If today is Monday, go back to Friday
            if today.weekday() == 0:  # Monday
                yesterday = today - timedelta(days=3)  # Friday

            start_date = datetime.combine(yesterday, datetime.min.time())
            end_date = datetime.combine(yesterday, datetime.max.time())

            logger.info(f"Loading previous day data for {instrument_id}")
            logger.info(f"Previous trading day: {yesterday}")

            bars = catalog.bars(
                instrument_ids=[instrument_id],
                start=start_date,
                end=end_date,
                as_nautilus=True,
            )

            if bars:
                bars.sort(key=lambda b: b.ts_init)
                logger.info(f"✅ Loaded {len(bars)} bars from previous day")
            else:
                logger.warning(f"No bars found for previous day: {yesterday}")

            return bars or []

        except Exception as e:
            logger.error(f"Failed to load previous day data: {e}")
            return []

    def _format_bar_time(self, bar) -> str:
        """Format bar timestamp for logging."""
        try:
            timestamp = bar.ts_init
            if timestamp > 1e12:  # Nanoseconds
                dt = datetime.fromtimestamp(timestamp / 1_000_000_000)
            else:  # Seconds
                dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "unknown"

    def get_warm_up_bars(
        self,
        instrument_id: str,
        sma_long_period: int,
        fractal_window: int = 5,
        strategy: str = "recent",
    ) -> List[Any]:
        """Get appropriate historical bars for warm-up based on strategy requirements.

        Args:
            instrument_id: The instrument ID to load data for
            sma_long_period: The long SMA period (determines minimum bars needed)
            fractal_window: Fractal window size
            strategy: Warm-up strategy - "recent" or "previous_day"

        Returns:
            List of historical bars for warm-up
        """
        # Calculate minimum bars needed for full warm-up
        min_bars_needed = max(sma_long_period, fractal_window)

        # Add 20% buffer to ensure we have enough data
        bars_to_load = int(min_bars_needed * 1.2)

        logger.info(
            f"Warm-up requirements: SMA={sma_long_period}, Fractal={fractal_window}"
        )
        logger.info(f"Loading {bars_to_load} bars for warm-up")

        if strategy == "previous_day":
            bars = self.load_previous_day_bars(instrument_id)
            # If we don't have enough from previous day, supplement with recent bars
            if len(bars) < min_bars_needed:
                logger.info(
                    f"Previous day has only {len(bars)} bars, loading recent bars"
                )
                bars = self.load_recent_bars(instrument_id, bars_to_load)
        else:
            bars = self.load_recent_bars(instrument_id, bars_to_load)

        return bars
