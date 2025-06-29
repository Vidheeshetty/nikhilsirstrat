import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strategies.my_nse_strategy.runners.backtest.backtest_orchestrator import (
    BacktestOrchestrator,
)
from strategies.my_nse_strategy.runners.backtest.results_processor import (
    ResultsProcessor,
)

# Use only 10 instruments for debug
INSTRUMENTS = [
    "NIFTY.OPT.03Jul2025.22850.CALL.NSE",
    "NIFTY.OPT.03Jul2025.22850.PUT.NSE",
    "NIFTY.OPT.03Jul2025.22800.PUT.NSE",
    "NIFTY.OPT.03Jul2025.22800.CALL.NSE",
    "NIFTY.OPT.03Jul2025.22950.CALL.NSE",
    "NIFTY.OPT.03Jul2025.22950.PUT.NSE",
    "NIFTY.OPT.03Jul2025.22900.CALL.NSE",
    "NIFTY.OPT.03Jul2025.22900.PUT.NSE",
    "NIFTY.OPT.03Jul2025.23000.CALL.NSE",
    "NIFTY.OPT.03Jul2025.23000.PUT.NSE",
]

CONFIG_FILE = "src/strategies/my_nse_strategy/config/strategy.yaml"
CATALOG_PATH = "catalog-data/my_nse_strategy/catalog"
BASE_DIR = "_summary.txts"

if __name__ == "__main__":
    orchestrator = BacktestOrchestrator(
        config_file=CONFIG_FILE, catalog_path=CATALOG_PATH, base_dir=BASE_DIR
    )
    results = []
    for instrument_id in INSTRUMENTS:
        print(f"\n=== Running backtest for {instrument_id} ===")
        result = orchestrator.run_single_backtest(
            instrument_id=instrument_id, verbose=False, batch_mode=True
        )
        # Print the full result object
        print(f"result object type: {type(result)}")
        print(f"result dir: {dir(result)}")
        print(f"result repr: {repr(result)}")
        # Print all attributes of result
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"  {k}: {v}")
        else:
            for attr in dir(result):
                if not attr.startswith("__"):
                    print(f"  {attr}: {getattr(result, attr)}")
        # Print stats_pnls if present
        print(f"result.stats_pnls: {getattr(result, 'stats_pnls', 'N/A')}")
        # Try to print the full account object if possible
        try:
            # This requires access to the engine, which is not returned by run_single_backtest
            # So we cannot print engine.cache.accounts() here unless the orchestrator exposes it
            pass
        except Exception as e:
            print(f"[DEBUG] Could not print account object: {e}")
        print(f"summary: {result}")
        account = result.get("account", None) if isinstance(result, dict) else None
        if account:
            print(f"account: {account}")
        else:
            print(
                f"account (from summary): {result.get('account_id', 'N/A') if isinstance(result, dict) else 'N/A'}, starting_balance: {result.get('starting_balance', 'N/A') if isinstance(result, dict) else 'N/A'}, ending_balance: {result.get('ending_balance', 'N/A') if isinstance(result, dict) else 'N/A'}"
            )
