# Backtesting Framework Optimization Suggestions

This document outlines opportunities to further optimize the backtesting framework, with a specific focus on enhancing modularity and streamlining reporting functionalities.

## A. What More Should Be Moved to `src/backtest_utils` (Particularly Reporting)

The goal is to consolidate generic, reusable logic into `src/backtest_utils` to improve maintainability, reduce redundancy, and facilitate easier development of new strategies.

1.  **Metric Calculation Logic:**
    *   **Current State:** Both `src/backtest_utils/report_generator.py` and `src/backtest_utils/results_aggregator.py` contain logic for calculating and formatting various performance metrics (e.g., PnL, Sharpe Ratio, drawdown). This can lead to duplicate code and potential inconsistencies if a calculation changes.
    *   **Suggestion:** Create a new dedicated module, `src/backtest_utils/metric_calculator.py`. This module would house all common logic for deriving standardized performance metrics from raw backtest results (e.g., `nautilus_trader.backtest.BacktestResult` objects). Both `ResultsAggregator` and `ReportGenerator` would then import and utilize functions from this `MetricCalculator` module to retrieve pre-calculated metrics, ensuring a single source of truth for these calculations.

2.  **Raw Data Extraction from Nautilus Trader Engine/Results:**
    *   **Current State:** The `ReportGenerator` and potentially `ResultsAggregator` (or their historical counterparts) directly interact with Nautilus Trader's internal `engine` or `result` objects to pull out fills, positions, orders, and account data for reporting.
    *   **Suggestion:** Introduce a `src/backtest_utils/data_extractor.py` module. This module would provide a clean, standardized API for extracting raw trade, position, order, and account data from Nautilus Trader `BacktestResult` objects or the engine's cache. This abstracts away the specifics of Nautilus Trader's internal data structures from the reporting and aggregation layers, making them more robust to changes in Nautilus Trader's API.

3.  **Flexible Data Formatting:**
    *   **Current State:** `ReportGenerator` uses a mix of `f-strings` and a `_safe_float_format` helper for presenting numerical data (currency, percentages, general floats). While functional, this can still be somewhat repetitive and less extensible.
    *   **Suggestion:** Develop a `src/backtest_utils/formatter.py` module. This module would centralize all data formatting utilities. It could offer functions like `format_currency(value, currency_code)`, `format_percentage(value, decimals)`, `format_number(value, decimals, thousand_separator)`. This ensures consistent formatting across all reports and simplifies future adjustments to numerical presentations.

4.  **Configuration for Reporting:**
    *   **Current State:** Certain aspects of report generation, such as the `base_dir` in `ReportGenerator` and some column width assumptions in tabular reports, are hardcoded.
    *   **Suggestion:** Expand the existing `config/backtest_config.json` or introduce a new `config/reporting_config.json`. This configuration file would allow users to specify report output paths, choose desired report types (e.g., summary only, detailed with trades, tabular), define default numerical formatting (e.g., number of decimal places for PnL), and configure column widths for tabular layouts, all without altering the codebase.

## B. How Reporting Can Be Further Optimized

Beyond moving common utilities, the reporting process itself can be made more flexible, robust, and user-friendly.

1.  **Enhanced Separation of Concerns within `ReportGenerator`:**
    *   **Current State:** The `ReportGenerator` class currently handles report generation, console printing, file writing, and the creation of various summary types (consolidated, tabular, with/without trades). This combines several distinct responsibilities.
    *   **Suggestion:** Further decompose `ReportGenerator` into more granular components:
        *   `ReportFormatter`: Dedicated solely to taking structured data (e.g., from `MetricCalculator` and `DataExtractor`) and rendering it into specific output formats (e.g., plain text, Markdown, potentially HTML or JSON). This class would not handle file I/O.
        *   `ReportWriter`: Responsible for handling file operations, taking formatted string content and writing it to specified log or summary files.
        *   `ReportOrchestrator` (or similar): A higher-level component that coordinates the data extraction, metric calculation, formatting, and writing processes. This centralizes the reporting workflow.

2.  **Structured Data Serialization for Advanced Analysis:**
    *   **Current State:** The primary outputs of the reporting system are text-based summary files. While human-readable, this format limits advanced programmatic analysis.
    *   **Suggestion:** Implement functionality to save detailed backtest results (including time series for PnL and equity curve, individual trades, positions, and orders) into structured data formats such as Parquet or CSV. This would allow users to easily load the data into analytical tools like Pandas DataFrames or external visualization libraries for deeper insights and custom charting. Consider creating a `results` folder for this purpose, alongside `backtest_results`.

3.  **Integration with Interactive Visualization Tools (Future Enhancement):**
    *   **Current State:** Reporting is limited to static text output.
    *   **Suggestion:** As a future enhancement, explore integrating with Python visualization libraries (e.g., `Plotly`, `Matplotlib`, `Dash`) to generate interactive charts and dashboards directly from the backtest results. This would significantly improve the user experience for analyzing performance, especially for batch runs involving many instruments. This would naturally follow from implementing structured data serialization.

4.  **Granular Logging Control for Report Details:**
    *   **Current State:** The `print_and_log_results` method outputs a broad range of information to both the console and log files.
    *   **Suggestion:** Leverage Python's `logging` module more effectively. Assign different logging levels (e.g., `INFO`, `DEBUG`) to various report details. For instance, high-level summaries could be logged at `INFO`, while individual trades and order details might be at `DEBUG`. This allows users to control the verbosity of their reports via standard logging configuration, without requiring code modifications.

5.  **Enhanced Error Handling and Robustness in Reporting:**
    *   **Current State:** While some `try-except` blocks exist, robust handling of missing or malformed data within calculations (e.g., `KeyError` for missing dictionary keys, `AttributeError` for missing object attributes) could be improved.
    *   **Suggestion:** Implement more explicit data validation checks and provide sensible default values or graceful error messages when expected data points are absent. This would make the reporting functions more resilient to incomplete or malformed `BacktestResult` objects, ensuring that reports are always generated, even if with some data gaps. 