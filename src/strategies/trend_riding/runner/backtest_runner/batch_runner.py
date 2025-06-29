from __future__ import annotations

from typing import Iterable, Dict, Any, List
from utils.runners.base_batch_runner import BatchRunner
from .single_runner import TrendRidingBacktestRunner

"""Batch runner for Trend-Riding strategy that utilises the generic BatchRunner."""


class TrendRidingBatchRunner:  # pylint: disable=too-few-public-methods
    """Run multiple instrument back-tests in parallel and aggregate results."""

    def __init__(self, max_workers: int | None = None):
        self._single_runner = TrendRidingBacktestRunner()
        self._batch = BatchRunner(self._single_runner.run, max_workers=max_workers)

    # ------------------------------------------------------------------
    def run(self, instruments: Iterable[str]) -> Dict[str, Any]:  # noqa: D401
        results: List[Dict[str, Any]] = self._batch.run(instruments)
        agg = BatchRunner.aggregate(results)
        agg["results"] = results

        # Generate reports
        from utils.reporting.controller import ReportController

        ReportController(mode="backtesting").generate(
            results, strategy_name="trend_riding"
        )

        return agg


__all__ = ["TrendRidingBatchRunner"]
