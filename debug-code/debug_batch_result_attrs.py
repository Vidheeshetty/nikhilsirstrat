import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strategies.my_nse_strategy.runners.backtest.backtest_orchestrator import BacktestOrchestrator
from strategies.my_nse_strategy.runners.backtest.results_processor import ResultsProcessor

# Use a small set of instruments for debug
INSTRUMENTS = [
    "NIFTY.OPT.03Jul2025.23450.PUT.NSE"
]

CONFIG_FILE = "src/strategies/my_nse_strategy/config/strategy.yaml"
CATALOG_PATH = "catalog-data/my_nse_strategy/catalog"
BASE_DIR = "_summary.txts"

def main():
    orchestrator = BacktestOrchestrator(
        config_file=CONFIG_FILE,
        catalog_path=CATALOG_PATH,
        base_dir=BASE_DIR
    )

    print("[DEBUG] Running batch backtest for:", INSTRUMENTS)
    results = orchestrator.run_batch_backtest(
        instrument_ids=INSTRUMENTS,
        verbose=True,
        max_workers=1
    )

    print("\n[DEBUG] Results returned from batch run:")
    for res in results:
        print(f"\nInstrument: {res.get('instrument_id')}")
        print(f"Summary keys: {list(res.keys())}")
        # Print all values
        for k, v in res.items():
            print(f"  {k}: {v}")
        # Print type and attributes if result object is present
        if 'result_obj' in res:
            result = res['result_obj']
            print(f"  [DEBUG] type(result): {type(result)}")
            print(f"  [DEBUG] dir(result): {dir(result)}")
            for attr in ['starting_balance', 'ending_balance', 'balance_free', 'balance_locked', 'base_currency', 'account_id']:
                print(f"    {attr}: {getattr(result, attr, None)}")
        else:
            print("  [DEBUG] No result_obj in summary.")

if __name__ == "__main__":
    main() 