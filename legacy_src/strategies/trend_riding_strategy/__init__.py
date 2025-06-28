"""Trend Riding Futures Strategy package.

This strategy is an early stub extracted from my_nse_strategy to illustrate
how strategies can depend on the shared helper stack in utils.runner while
remaining fully independent from other strategy packages.
"""

from importlib.metadata import PackageNotFoundError, version as _v

try:
    __version__ = _v("trend_riding_strategy")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"  # placeholder 