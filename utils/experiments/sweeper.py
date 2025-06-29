from __future__ import annotations

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
from typing import Type, Any, Dict, Iterable, List

"""Parameter sweeping utilities for strategy optimization.

Provides ParameterSweeper class that can run multiple backtest configurations
in parallel, generating combinations from parameter ranges and collecting
results for analysis.

Supports both single-threaded and multi-threaded execution with configurable
worker pools for efficient parameter space exploration.

Examples
--------
>>> from utils.experiments.sweeper import ParameterSweeper
>>> from src.strategies.swing_range_expansion.runner.backtest_runner import SwingRangeExpansionBacktestRunner

>>> # Define parameter grid
>>> grid = {
...     'nr_lookback': [5, 7, 10],
...     'target_rr': [1.0, 1.5, 2.0],
...     'stop_rr': [0.5, 0.75, 1.0]
... }

>>> # Run parameter sweep
>>> sweeper = ParameterSweeper(SwingRangeExpansionBacktestRunner)
>>> results_df = run_parameter_sweep(SwingRangeExpansionBacktestRunner, grid, ["NIFTY.D.NSE"])
"""


def _iter_grid(param_grid: Dict[str, Iterable[Any]]):  # noqa: D401
    keys = list(param_grid)
    for values in product(*[param_grid[k] for k in keys]):
        yield dict(zip(keys, values))


# ------------------------------------------------------------------


def _run_single(
    runner_cls: Type,  # noqa: ANN001 – generic strategy runner class
    params: Dict[str, Any],
    instrument_id: str,
) -> Dict[str, Any]:
    """Instantiate runner_cls → run(instrument_id, **params) → return metrics."""
    runner = runner_cls()
    result = runner.run(instrument_id, **params)  # type: ignore[arg-type]
    result["_params"] = params
    return result


# ------------------------------------------------------------------


def run_parameter_sweep(
    runner_cls: Type,  # noqa: ANN001 – expected to expose .run()
    param_grid: Dict[str, Iterable[Any]],
    instrument_ids: List[str],
    *,
    workers: int = 4,
) -> pd.DataFrame:  # noqa: D401
    """Execute grid search over *param_grid* for each instrument.

    Returns a tidy DataFrame with metrics + flattened param columns.
    """

    tasks = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for ins in instrument_ids:
            for params in _iter_grid(param_grid):
                fut = pool.submit(_run_single, runner_cls, params, ins)
                tasks.append(fut)

        rows: List[Dict[str, Any]] = []
        for fut in as_completed(tasks):
            try:
                res = fut.result()
                row = {**res, **res.pop("_params", {})}
                rows.append(row)
            except Exception as exc:  # pragma: no cover
                rows.append({"error": str(exc)})

    df = pd.DataFrame(rows)
    return df


__all__ = ["run_parameter_sweep"]
