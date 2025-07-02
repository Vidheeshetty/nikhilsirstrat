import pandas as pd
from pathlib import Path

from utils.data_adapters.conversion_config import ConverterConfig
from scripts.data_import import csv_to_parquet_converter as conv


def _create_sample_csv(tmp_path: Path) -> Path:
    raw_dir = (
        tmp_path
        / "raw-data/source=TEST/instrument=FUT/venue=SIM/symbol=FOO/timeframe=DAILY/year=2024"
    )
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = raw_dir / "FOO_2024.csv"
    df = pd.DataFrame(
        {
            "SYMBOL": ["FOO"],
            "DATE": ["2024-01-02"],
            "EXPIRY_DT": ["2024-01-25"],
            "OPEN": [100],
            "HIGH": [110],
            "LOW": [95],
            "CLOSE": [105],
            "OI": [1000],
            "IV": [0.2],
        }
    )
    df.to_csv(csv_path, index=False)
    return csv_path


def _sample_config(tmp_path: Path) -> Path:
    cfg_yaml = tmp_path / "cfg.yaml"
    cfg_yaml.write_text(
        f"""
source_csv: '{tmp_path}/raw-data/source=TEST/instrument=FUT/venue=SIM/symbol=FOO/timeframe=DAILY/year=*/FOO_*.csv'

destination_catalog: '{tmp_path}/catalog-data/source=TEST/instrument=FUT/venue=SIM/symbol=FOO/timeframe=DAILY/'
destination_meta: '{tmp_path}/catalog-data/_meta/source=TEST/instrument=FUT/venue=SIM/symbol=FOO/'

symbol: 'FOO'
venue: 'SIM'
data_kind: 'bar'
bar_interval: '1-DAY'
price_precision: 2
price_increment: 0.01
multiplier: 1
extra_meta_fields: ['OI', 'IV']
"""
    )
    return cfg_yaml


def test_end_to_end_conversion(tmp_path, monkeypatch):
    # 1. prepare raw csv and config
    _create_sample_csv(tmp_path)
    cfg_file = _sample_config(tmp_path)
    cfg = ConverterConfig.from_yaml(cfg_file)

    # 2. stub ParquetDataCatalog to avoid heavy dependency
    class _StubCatalog:
        def __init__(self, *_):
            self.instruments = []
            self.bars = []

        def write_data(self, data):
            # naive split detection
            if hasattr(data, "__iter__"):
                if len(data) and hasattr(data[0], "bar_type"):
                    self.bars.extend(data)
                else:
                    self.instruments.extend(data)

    monkeypatch.setattr(conv, "ParquetDataCatalog", _StubCatalog, raising=True)

    # 3. run conversion
    conv.run_conversion(cfg)

    # 4. verify catalog dirs created
    assert (Path(cfg.destination_catalog)).exists()

    # 5. verify inventory doc created
    md_path = Path("DATA_CATALOG.md")
    assert md_path.exists(), "DATA_CATALOG.md not generated"
    content = md_path.read_text()
    assert "FOO" in content, "Expected instrument symbol not present in DATA_CATALOG.md"
