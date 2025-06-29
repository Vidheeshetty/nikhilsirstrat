# Placeholder for generic batch helper functions.
# Move and refactor code from batch_helpers.py here, removing strategy-specific logic.

from typing import Optional, Dict, Any, Type


def run_single_backtest_wrapper_for_pool(
    batch_runner_class: Type,
    config_manager,
    data_manager,
    engine_manager,
    results_processor,
    report_generator,
    instrument_id: str,
    strategy_class: Type,
    start_time: Optional[str],
    end_time: Optional[str],
    verbose: bool,
    batch_mode: bool = True,
) -> Dict[str, Any]:
    """Standalone wrapper for running a single backtest in a process pool (generic version)."""
    try:
        runner = batch_runner_class(
            config_manager=config_manager,
            data_manager=data_manager,
            engine_manager=engine_manager,
            results_processor=results_processor,
            report_generator=report_generator,
        )
        return runner.run_single_backtest(
            instrument_id=instrument_id,
            strategy_class=strategy_class,
            start_time=start_time,
            end_time=end_time,
            log_file=None,
            verbose=verbose,
            batch_mode=batch_mode,
        )
    except Exception as e:
        return {"instrument_id": instrument_id, "error": str(e)}
