from utils.data.data_manager import DataManager


def test_data_manager_quotes():
    dm = DataManager()
    prices = dm.get_trade_ticks("NIFTY.FUT.NSE", allow_stub=True)
    assert len(prices) > 0


def test_data_manager_start_end():
    dm = DataManager()
    prices = dm.get_trade_ticks(
        "NIFTY.FUT.NSE", start="2023-01-01", end="2023-01-31", allow_stub=True
    )
    assert isinstance(prices, list)
