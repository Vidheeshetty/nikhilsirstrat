"""
Generic Data Loader for Backtesting

This module provides a generic data loader for backtesting strategies.
It handles loading data from Parquet catalogs and managing instrument data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog


class DataLoader:
    """Generic data loader for backtesting."""

    def __init__(self):
        """Initialize the data loader."""
        pass

    def load_instrument_data(
        self,
        instrument_id: str,
        start_date: str,
        end_date: str,
        catalog_path: str = "catalog-data",
    ) -> Optional[Dict[str, Any]]:
        """
        Load data for a specific instrument.

        Args:
            instrument_id: The instrument ID to load data for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            catalog_path: Path to the data catalog

        Returns:
            Dictionary containing instrument data or None if not found
        """
        try:
            # Initialize catalog
            catalog = ParquetDataCatalog(catalog_path)

            # Convert dates to datetime
            start_dt = datetime.fromisoformat(f"{start_date}T00:00:00")
            end_dt = datetime.fromisoformat(f"{end_date}T23:59:59")

            # Load quote ticks
            ticks = catalog.quote_ticks(
                instrument_ids=[instrument_id],
                start=start_dt,
                end=end_dt,
                as_nautilus=True,
            )

            if not ticks:
                return None

            # Load instrument info
            instruments = catalog.instruments(
                instrument_ids=[instrument_id],
                as_nautilus=True,
            )

            return {
                "instrument_id": instrument_id,
                "ticks": ticks,
                "instrument": instruments[0] if instruments else None,
                "start_date": start_date,
                "end_date": end_date,
            }

        except Exception as e:
            print(f"Error loading data for {instrument_id}: {e}")
            return None

    def get_available_instruments(
        self, catalog_path: str = "catalog-data"
    ) -> List[str]:
        """
        Get list of available instruments in the catalog.

        Args:
            catalog_path: Path to the data catalog

        Returns:
            List of available instrument IDs
        """
        try:
            catalog = ParquetDataCatalog(catalog_path)
            instruments = catalog.instruments(as_nautilus=True)
            return [str(instrument.id) for instrument in instruments]
        except Exception as e:
            print(f"Error getting available instruments: {e}")
            return []

    def validate_data_exists(
        self,
        instrument_id: str,
        start_date: str,
        end_date: str,
        catalog_path: str = "catalog-data",
    ) -> bool:
        """
        Validate that data exists for the given instrument and date range.

        Args:
            instrument_id: The instrument ID to validate
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            catalog_path: Path to the data catalog

        Returns:
            True if data exists, False otherwise
        """
        data = self.load_instrument_data(
            instrument_id, start_date, end_date, catalog_path
        )
        return data is not None and len(data.get("ticks", [])) > 0
