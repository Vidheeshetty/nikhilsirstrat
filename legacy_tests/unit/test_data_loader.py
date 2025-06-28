import pytest
import os
from pathlib import Path
from datetime import datetime, timezone
import shutil

from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.model.enums import AssetClass, OptionKind
from nautilus_trader.model.instruments.option_contract import OptionContract
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

# Ensure src is in sys.path for local imports
import sys
current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.data_loader import DataManager # Note: It was DataLoader in my previous internal model, but it's DataManager in your code


@pytest.fixture(scope="module")
def setup_catalog_for_data_loader(tmp_path_factory):
    """
    Sets up a dummy Parquet data catalog with some instruments and quote ticks
    for testing the DataManager.
    """
    catalog_base_dir = tmp_path_factory.mktemp("test_dataloader_catalog")
    catalog_path = catalog_base_dir / "catalog"
    catalog_meta_path = catalog_base_dir / "catalog-meta"

    catalog = ParquetDataCatalog(str(catalog_path))

    # Create dummy instrument
    instrument_id_str = "NIFTY.OPT.19Jun2025.24800.PUT.NSE"
    symbol_val = "NIFTY"
    venue_val = "NSE"
    expiry_raw = "19Jun2025"
    strike_val = 24800.0
    right_val = "PUT"

    expiry_dt = datetime.strptime(expiry_raw, "%d%b%Y")
    expiry_utc = expiry_dt.replace(hour=15, minute=30, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    test_instrument = OptionContract(
        instrument_id=InstrumentId(symbol=Symbol(f"{symbol_val}.OPT.{expiry_raw}.{int(strike_val)}.{right_val}"), venue=Venue(venue_val)),
        raw_symbol=Symbol(symbol_val),
        asset_class=AssetClass.INDEX,
        exchange=venue_val,
        currency=Currency.from_str("INR"),
        price_precision=2,
        price_increment=Price(0.05, 2),
        multiplier=Quantity(15, 0),
        lot_size=Quantity(1, 0),
        underlying=f"{symbol_val}.{venue_val}.INDEX",
        option_kind=OptionKind[right_val],
        strike_price=Price(strike_val, 2),
        activation_ns=0,
        expiration_ns=dt_to_unix_nanos(expiry_utc),
        ts_event=dt_to_unix_nanos(now_utc),
        ts_init=dt_to_unix_nanos(now_utc),
    )
    catalog.write_data([test_instrument])

    # Create dummy quote ticks
    from nautilus_trader.model.data import QuoteTick
    ticks = [
        QuoteTick(
            instrument_id=test_instrument.id,
            ts_event=dt_to_unix_nanos(datetime(2025, 6, 18, 9, 15, 0, tzinfo=timezone.utc)),
            ts_init=dt_to_unix_nanos(datetime(2025, 6, 18, 9, 15, 0, tzinfo=timezone.utc)),
            bid_price=Price(100.50, 2),
            ask_price=Price(101.50, 2),
            bid_size=Quantity(100, 0),
            ask_size=Quantity(100, 0),
        ),
        QuoteTick(
            instrument_id=test_instrument.id,
            ts_event=dt_to_unix_nanos(datetime(2025, 6, 18, 9, 16, 0, tzinfo=timezone.utc)),
            ts_init=dt_to_unix_nanos(datetime(2025, 6, 18, 9, 16, 0, tzinfo=timezone.utc)),
            bid_price=Price(100.60, 2),
            ask_price=Price(101.60, 2),
            bid_size=Quantity(120, 0),
            ask_size=Quantity(120, 0),
        ),
    ]
    catalog.write_data(ticks)

    yield str(catalog_path), str(catalog_meta_path), str(test_instrument.id), ticks


class TestDataManager:

    def test_get_all_instrument_ids(self, setup_catalog_for_data_loader):
        catalog_path, _, expected_instrument_id, _ = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        instrument_ids = data_manager.get_all_instrument_ids()
        assert len(instrument_ids) > 0
        assert expected_instrument_id in instrument_ids

    def test_get_instrument(self, setup_catalog_for_data_loader):
        catalog_path, _, expected_instrument_id, _ = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        instrument = data_manager.get_instrument(expected_instrument_id)
        assert instrument is not None
        assert str(instrument.id) == expected_instrument_id

    def test_get_instrument_not_found(self, setup_catalog_for_data_loader):
        catalog_path, _, _, _ = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        with pytest.raises(ValueError, match="Instrument not found"):
            data_manager.get_instrument("NON_EXISTENT.INSTRUMENT.ID")

    def test_get_quote_ticks(self, setup_catalog_for_data_loader):
        catalog_path, _, expected_instrument_id, expected_ticks = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        start_time = "2025-06-18T09:15:00"
        end_time = "2025-06-18T09:16:00"
        ticks = data_manager.get_quote_ticks(expected_instrument_id, start_time, end_time)
        assert len(ticks) == len(expected_ticks)
        assert ticks[0].instrument_id == expected_ticks[0].instrument_id

    def test_validate_instrument_data_exists(self, setup_catalog_for_data_loader):
        catalog_path, _, expected_instrument_id, _ = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        start_time = "2025-06-18T09:15:00"
        end_time = "2025-06-18T09:16:00"
        assert data_manager.validate_instrument_data(expected_instrument_id, start_time, end_time) is True

    def test_validate_instrument_data_not_exists(self, setup_catalog_for_data_loader):
        catalog_path, _, _, _ = setup_catalog_for_data_loader
        data_manager = DataManager(catalog_path=catalog_path)
        # Test non-existent instrument
        assert data_manager.validate_instrument_data("NON_EXISTENT.ID", "2025-01-01", "2025-01-02") is False
        # Test existing instrument but no data in range
        assert data_manager.validate_instrument_data(setup_catalog_for_data_loader[2], "2026-01-01", "2026-01-02") is False 