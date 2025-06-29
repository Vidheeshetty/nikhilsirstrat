from typing import Optional, Dict, Any


def run_single_backtest_wrapper_for_pool(
    config_file: str,
    catalog_path: str,
    base_dir: str,
    instrument_id: str,
    start_time: Optional[str],
    end_time: Optional[str],
    verbose: bool,
    batch_mode: bool = True,
) -> Dict[str, Any]:
    """Standalone wrapper for running a single backtest in a process pool."""
    try:
        from .backtest_orchestrator import BacktestOrchestrator

        orchestrator = BacktestOrchestrator(
            config_file=config_file, catalog_path=catalog_path, base_dir=base_dir
        )
        return orchestrator.run_single_backtest(
            instrument_id=instrument_id,
            start_time=start_time,
            end_time=end_time,
            log_file=None,
            verbose=verbose,
            batch_mode=batch_mode,
        )
    except Exception as e:
        return {"instrument_id": instrument_id, "error": str(e)}
