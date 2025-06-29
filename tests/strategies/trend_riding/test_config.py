from strategies.trend_riding.config import TrendRidingConfig


def test_config_defaults():
    cfg = TrendRidingConfig(instrument_id="TEST_FUT.NSE")
    assert cfg.lookback_intervals == 20
    assert cfg.sl_pct == 0.02
    assert cfg.tp_pct == 0.04
    assert cfg.position_size == 1
