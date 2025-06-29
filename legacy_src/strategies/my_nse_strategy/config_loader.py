from backtest_utils.config_loader import BacktestConfigLoader
from .config import MyNSEStrategyConfig
import inspect


class MyNSEStrategyConfigLoader(BacktestConfigLoader):
    """
    A strategy-specific config loader for MyNSEStrategy.
    """

    def get_strategy_config(
        self, instrument_id_override: str = None
    ) -> MyNSEStrategyConfig:
        """
        Creates a MyNSEStrategyConfig object from the loaded configuration.
        """
        config_data = super().get_strategy_config()

        if instrument_id_override:
            config_data["instrument_id"] = instrument_id_override

        # Filter only the arguments that MyNSEStrategyConfig expects
        sig = inspect.signature(MyNSEStrategyConfig)
        strategy_keys = set(sig.parameters.keys())
        filtered_config_data = {
            k: v for k, v in config_data.items() if k in strategy_keys
        }

        return MyNSEStrategyConfig(**filtered_config_data)
