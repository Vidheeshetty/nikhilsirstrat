import pytest
import yaml
from pathlib import Path
from datetime import datetime  # Import datetime

# Ensure src is in sys.path for local imports
import sys

current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.config_loader import BacktestConfigLoader


@pytest.fixture(scope="function")
def setup_config_file(tmp_path):
    """
    Creates a dummy YAML config file for testing.
    """
    config_content = """
instrument_id: TEST.INST.ID
start_time: 2025-01-01T00:00:00
end_time: 2025-01-02T00:00:00
catalog_path: /tmp/catalog
meta_catalog_path: /tmp/meta_catalog # Added meta_catalog_path
sl_pct: 0.01
tp_pct: 0.02
min_qty: 1
max_qty: 100
leverage: 1
fixed_qty: 10
"""
    config_file = tmp_path / "test_strategy.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture(scope="function")
def setup_invalid_config_file(tmp_path):
    """
    Creates a dummy invalid YAML config file for testing.
    """
    invalid_config_content = """
instrument_id: INVALID.ID
start_time: invalid-time
"""
    config_file = tmp_path / "invalid_strategy.yaml"
    config_file.write_text(invalid_config_content)
    return str(config_file)


@pytest.fixture(scope="function")
def setup_missing_field_config_file(tmp_path):
    """
    Creates a dummy YAML config file with a missing required field.
    """
    missing_field_content = """
instrument_id: MISSING.FIELD.ID
start_time: 2025-01-01T00:00:00
end_time: 2025-01-02T00:00:00
catalog_path: /tmp/catalog
# meta_catalog_path is missing
sl_pct: 0.01
tp_pct: 0.02
min_qty: 1
max_qty: 100
leverage: 1
fixed_qty: 10
"""
    config_file = tmp_path / "missing_field.yaml"
    config_file.write_text(missing_field_content)
    return str(config_file)


class TestBacktestConfigLoader:
    def test_load_config_success(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        config = config_loader.load_config()
        assert isinstance(config, dict)
        assert config["instrument_id"] == "TEST.INST.ID"
        assert config["start_time"] == datetime(
            2025, 1, 1, 0, 0
        )  # Changed to datetime object
        assert config["end_time"] == datetime(
            2025, 1, 2, 0, 0
        )  # Changed to datetime object

    def test_load_config_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            BacktestConfigLoader("non_existent_config.yaml").load_config()

    def test_load_config_invalid_yaml(self, tmp_path):
        malformed_yaml = tmp_path / "malformed.yaml"
        malformed_yaml.write_text("key: [invalid: yaml")
        with pytest.raises(ValueError, match="Invalid YAML in configuration file"):
            BacktestConfigLoader(str(malformed_yaml)).load_config()

    def test_get_config_value(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        value = config_loader.get("sl_pct")
        assert value == 0.01
        assert config_loader.get("non_existent_key", "default_val") == "default_val"

    def test_validate_config_success(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        assert config_loader.validate_config() is True

    def test_validate_config_missing_field(self, setup_missing_field_config_file):
        config_loader = BacktestConfigLoader(setup_missing_field_config_file)
        with pytest.raises(
            ValueError,
            match="Missing required configuration field: (meta_catalog_path|min_qty|max_qty|leverage|fixed_qty)",
        ):
            config_loader.validate_config()

    def test_get_strategy_config(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        strategy_config = config_loader.get_strategy_config("OVERRIDE.INST.ID")
        assert str(strategy_config.instrument_id) == "OVERRIDE.INST.ID"
        assert strategy_config.sl_pct == 0.01
        assert not hasattr(strategy_config, "start_time")  # Should be removed

    def test_get_strategy_config_from_yaml_if_no_cli_override(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        strategy_config = config_loader.get_strategy_config(None)  # No CLI override
        assert str(strategy_config.instrument_id) == "TEST.INST.ID"

    def test_get_strategy_config_no_instrument_id(self, tmp_path):
        no_inst_config_content = """
start_time: 2025-01-01T00:00:00
end_time: 2025-01-02T00:00:00
catalog_path: /tmp/catalog
meta_catalog_path: /tmp/meta_catalog
sl_pct: 0.01
tp_pct: 0.02
min_qty: 1
max_qty: 100
leverage: 1
fixed_qty: 10
"""
        config_file = tmp_path / "no_instrument.yaml"
        config_file.write_text(no_inst_config_content)
        config_loader = BacktestConfigLoader(str(config_file))
        with pytest.raises(ValueError, match="No instrument_id provided"):
            config_loader.get_strategy_config(None)

    def test_get_backtest_params(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        # Test with overrides
        params = config_loader.get_backtest_params(
            "2025-02-01T00:00:00", "2025-02-02T00:00:00"
        )
        assert params["start_time"] == datetime(
            2025, 2, 1, 0, 0
        )  # Changed to datetime object
        assert params["end_time"] == datetime(
            2025, 2, 2, 0, 0
        )  # Changed to datetime object
        from nautilus_trader.model.currencies import INR

        assert params["base_currency"] == INR

    def test_get_backtest_params_from_config(self, setup_config_file):
        config_loader = BacktestConfigLoader(setup_config_file)
        # Ensure initial config is loaded, then test with no overrides
        config_loader.load_config()
        params = config_loader.get_backtest_params(None, None)
        assert params["start_time"] == datetime(
            2025, 1, 1, 0, 0
        )  # Changed to datetime object
        assert params["end_time"] == datetime(
            2025, 1, 2, 0, 0
        )  # Changed to datetime object
