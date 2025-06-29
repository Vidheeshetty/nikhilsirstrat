#!/usr/bin/env python3
"""
MyNSEStrategy Runners Package

This package provides modular components for running MyNSEStrategy in different modes.
Currently supports:
- Backtest: Complete backtesting framework
- ReportGenerator: Report generation utilities

Future support planned:
- PaperTrading: Paper trading execution
- LiveTrading: Live trading execution
"""

from .report_generator import ReportGenerator
from .backtest import (
    BacktestOrchestrator,
    ConfigManager,
    DataManager,
    EngineManager,
    ResultsProcessor,
)

__all__ = [
    "ReportGenerator",
    "BacktestOrchestrator",
    "ConfigManager",
    "DataManager",
    "EngineManager",
    "ResultsProcessor",
]
