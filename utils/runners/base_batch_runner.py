from __future__ import annotations

import concurrent.futures as _fut
import logging
from typing import Callable, Any, Iterable, List, Dict

"""Generic batch runner infrastructure.

Provides BatchRunner class that can execute any worker function across
multiple inputs in parallel using ThreadPoolExecutor. Handles result
aggregation and provides common batch processing patterns.

Used as foundation for strategy-specific batch runners.

The design is intentionally simple and lightweight so strategy-specific batch runners
can be unit-tested quickly.
"""

logger = logging.getLogger(__name__)


class BatchRunner:  # pylint: disable=too-few-public-methods
    """Run tasks in parallel threads and collate results."""

    def __init__(
        self, worker_fn: Callable[[Any], Dict[str, Any]], max_workers: int | None = None
    ):
        """Args
        -----
        worker_fn: Callable that processes a single task object and returns a
            *dict* summary (must contain an ``instrument_id`` key for collation).
        max_workers: Concurrency level; defaults to ``min(32, os.cpu_count() + 4)``.
        """
        self._worker = worker_fn
        self._max_workers = max_workers

    # ------------------------------------------------------------------
    def run(self, tasks: Iterable[Any]) -> List[Dict[str, Any]]:  # noqa: D401
        """Execute *tasks* in parallel and return list of summaries."""
        results: list[Dict[str, Any]] = []
        with _fut.ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            fut_to_task = {pool.submit(self._worker, t): t for t in tasks}
            for fut in _fut.as_completed(fut_to_task):
                task = fut_to_task[fut]
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.exception("Task %s raised exception: %s", task, exc)
        return results

    # ------------------------------------------------------------------
    @staticmethod
    def aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:  # noqa: D401
        """Aggregate list of summaries into a high-level summary.

        Currently just counts successes and collects PnL sum if present.
        """
        agg: dict[str, Any] = {
            "num_instruments": len(results),
            "total_pnl": sum(r.get("pnl", 0.0) for r in results),
            "avg_sharpe": (sum(r.get("sharpe", 0.0) for r in results) / len(results))
            if results
            else 0.0,
            "avg_mdd_pct": (
                sum(r.get("mdd_pct", r.get("max_drawdown_pct", 0.0)) for r in results)
                / len(results)
            )
            if results
            else 0.0,
        }
        return agg


__all__ = ["BatchRunner"]
