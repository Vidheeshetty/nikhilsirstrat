from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict

"""Base strategy framework for backtesting.

Provides abstract base classes for strategies and their configurations,
establishing common interfaces that can be used across different strategy
implementations without tight coupling to specific trading frameworks.

The design supports both simple backtesting scenarios and more complex
live trading integrations.
"""


@dataclass
class StrategyConfigBase:  # pylint: disable=too-few-public-methods
    """Base dataclass from which concrete strategy configs inherit."""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict representation suitable for serialization."""
        return asdict(self)


class BaseStrategy:  # pylint: disable=too-few-public-methods
    """Abstract parent for all strategies in this codebase."""

    config_class = StrategyConfigBase

    def __init__(self, config: StrategyConfigBase | Dict[str, Any]):
        if isinstance(config, dict):
            # Allow passing plain dicts in tests
            self.config = self.config_class(**config)  # type: ignore[arg-type]
        else:
            self.config = config
        self.log = logging.getLogger(self.__class__.__name__)
        self._setup()

    # ------------------------------------------------------------------
    # Lifecycle helpers – subclasses can override where relevant
    # ------------------------------------------------------------------
    def _setup(self) -> None:  # noqa: D401
        """Optional internal setup after __init__."""
        self.log.debug("Strategy set-up complete with config: %s", self.config)

    def on_quote(self, quote):  # noqa: D401
        raise NotImplementedError

    def on_bar(self, bar):  # noqa: D401
        raise NotImplementedError

    def on_stop(self) -> None:  # noqa: D401
        self.log.info("Strategy stopped – override in subclass if needed.")

    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # noqa: D401
        return f"{self.__class__.__name__}({self.config})"
