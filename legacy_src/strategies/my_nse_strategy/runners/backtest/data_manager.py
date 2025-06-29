#!/usr/bin/env python3
"""
Data Manager for MyNSEStrategy Backtesting

Handles data catalog operations, instrument discovery, and data loading.
"""

from pathlib import Path
from typing import List, Optional
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId


class DataManager:
    """Manages data catalog operations and data loading."""

    def __init__(self, catalog_path: str):
        self.catalog_path = catalog_path
        self.catalog = ParquetDataCatalog(catalog_path)

    def get_all_instrument_ids(self) -> List[str]:
        """Get all instrument IDs from the data catalog."""
        instrument_ids = set()

        # Define the data type directories to scan
        data_types = ["quote_tick", "option_contract"]

        for data_type in data_types:
            data_path = Path(self.catalog_path) / "data" / data_type

            if not data_path.exists() or not data_path.is_dir():
                print(f"Warning: Directory not found at {data_path}")
                continue

            # Get all subdirectories, which are assumed to be instrument IDs
            for d in data_path.iterdir():
                if d.is_dir():
                    instrument_ids.add(d.name)

        return sorted(list(instrument_ids))

    def get_instrument(self, instrument_id: str):
        """Get instrument data from catalog."""
        instruments = self.catalog.instruments(
            instrument_ids=[instrument_id],
            as_nautilus=True,
        )
        if not instruments:
            raise ValueError(f"Instrument not found: {instrument_id}")
        return instruments[0]

    def get_quote_ticks(self, instrument_id: str, start_time: str, end_time: str):
        """Get quote tick data for backtesting."""
        return self.catalog.quote_ticks(
            instrument_ids=[instrument_id],
            start=start_time,
            end=end_time,
            as_nautilus=True,
        )

    def validate_instrument_data(
        self, instrument_id: str, start_time: str, end_time: str
    ) -> bool:
        """Validate that instrument has data for the specified time range."""
        try:
            ticks = self.get_quote_ticks(instrument_id, start_time, end_time)
            return len(ticks) > 0
        except Exception:
            return False
