import pandas as pd
from scripts.data_import.csv_to_parquet_converter import build_bar_metadata


def test_build_bar_metadata():
    df = pd.DataFrame(
        {
            "DATE": ["2023-01-01", "2023-01-02"],
            "CLOSE": [100, 101],
            "IV": [0.2, 0.25],
            "OI": [1000, 1200],
        }
    )
    df["DATE"] = pd.to_datetime(df["DATE"], utc=True)

    extras = ["impliedVolatility", "openInterest"]
    meta = build_bar_metadata(df, "TEST.FUT.NSE", extras)

    # Expect base columns + extra fields
    assert set(["instrument_id", "timestamp", "last", *extras]).issubset(meta.columns)
    assert len(meta) == 2
