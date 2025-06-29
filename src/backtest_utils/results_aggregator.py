"""
Generic Results Aggregator for Backtesting

This module provides a generic results aggregator for backtesting strategies.
It handles aggregating and processing backtest results from multiple runs.
"""

import os
from typing import Dict, Any, List
from datetime import datetime


class ResultsAggregator:
    """Generic results aggregator for backtesting."""

    def __init__(self):
        """Initialize the results aggregator."""
        pass

    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple backtest runs.

        Args:
            results: List of backtest result dictionaries

        Returns:
            Dictionary containing aggregated results
        """
        if not results:
            return {}

        aggregated = {
            "total_runs": len(results),
            "successful_runs": 0,
            "failed_runs": 0,
            "total_return": 0.0,
            "avg_return": 0.0,
            "total_trades": 0,
            "avg_trades": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "results": results,
        }

        successful_results = []

        for result in results:
            if result and "result" in result:
                try:
                    backtest_result = result["result"]
                    successful_results.append(backtest_result)

                    # Aggregate metrics
                    aggregated["total_return"] += getattr(
                        backtest_result, "total_return", 0.0
                    )
                    aggregated["total_trades"] += getattr(
                        backtest_result, "total_trades", 0
                    )

                    # Track max drawdown
                    max_dd = getattr(backtest_result, "max_drawdown", 0.0)
                    if abs(max_dd) > abs(aggregated["max_drawdown"]):
                        aggregated["max_drawdown"] = max_dd

                except Exception as e:
                    print(f"Error processing result: {e}")
                    aggregated["failed_runs"] += 1
            else:
                aggregated["failed_runs"] += 1

        aggregated["successful_runs"] = len(successful_results)

        # Calculate averages
        if aggregated["successful_runs"] > 0:
            aggregated["avg_return"] = (
                aggregated["total_return"] / aggregated["successful_runs"]
            )
            aggregated["avg_trades"] = (
                aggregated["total_trades"] / aggregated["successful_runs"]
            )

            # Calculate average Sharpe ratio
            sharpe_sum = sum(
                getattr(r, "sharpe_ratio", 0.0) for r in successful_results
            )
            aggregated["sharpe_ratio"] = sharpe_sum / aggregated["successful_runs"]

            # Calculate average win rate
            win_rate_sum = sum(getattr(r, "win_rate", 0.0) for r in successful_results)
            aggregated["win_rate"] = win_rate_sum / aggregated["successful_runs"]

        return aggregated

    def save_aggregated_results(
        self, aggregated_results: Dict[str, Any], output_dir: str = "backtest_results"
    ) -> str:
        """
        Save aggregated results to a file.

        Args:
            aggregated_results: Aggregated results dictionary
            output_dir: Directory to save results

        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%H-%M-%S")

        # Save summary
        summary_file = os.path.join(output_dir, f"aggregated_summary_{timestamp}.txt")
        with open(summary_file, "w") as f:
            f.write("Aggregated Backtest Results Summary\n")
            f.write("===================================\n")
            f.write(f"Total Runs: {aggregated_results.get('total_runs', 0)}\n")
            f.write(
                f"Successful Runs: {aggregated_results.get('successful_runs', 0)}\n"
            )
            f.write(f"Failed Runs: {aggregated_results.get('failed_runs', 0)}\n")
            f.write(
                f"Total Return: {aggregated_results.get('total_return', 0.0):.4f}\n"
            )
            f.write(
                f"Average Return: {aggregated_results.get('avg_return', 0.0):.4f}\n"
            )
            f.write(f"Total Trades: {aggregated_results.get('total_trades', 0)}\n")
            f.write(
                f"Average Trades: {aggregated_results.get('avg_trades', 0.0):.2f}\n"
            )
            f.write(f"Win Rate: {aggregated_results.get('win_rate', 0.0):.4f}\n")
            f.write(
                f"Sharpe Ratio: {aggregated_results.get('sharpe_ratio', 0.0):.4f}\n"
            )
            f.write(
                f"Max Drawdown: {aggregated_results.get('max_drawdown', 0.0):.4f}\n"
            )

        return summary_file
