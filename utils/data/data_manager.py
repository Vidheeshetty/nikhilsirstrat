from __future__ import annotations

"""DataManager – supplies price series for an instrument.

Currently generates synthetic monotonically increasing prices. When the real
Parquet catalog is ready, we will load bars/ticks from there.
"""

from typing import List


class DataManager:  # pylint: disable=too-few-public-methods
    """Return price series; prefers real parquet catalog if available."""

    def __init__(self, catalog_path: str | None = None):
        self.catalog_path = catalog_path or "catalog-data/shared/catalog"
        # Lazy import so tests without nautilus pass.
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog  # type: ignore

            self._catalog = ParquetDataCatalog(self.catalog_path)
        except Exception:  # pylint: disable=broad-except
            self._catalog = None

    # ------------------------------------------------------------------
    def get_quote_ticks(self, instrument_id: str, start=None, end=None) -> List[float]:  # noqa: D401
        if self._catalog is None:
            return self._synthetic_prices(instrument_id)

        try:
            # Convert optional start/end to nanoseconds if provided (ISO or int)
            def _to_ns(val):
                if val is None:
                    return None
                try:
                    from nautilus_trader.core.datetime import dt_to_unix_nanos  # type: ignore
                    from datetime import datetime
                    if isinstance(val, (int, float)):
                        return int(val)
                    if isinstance(val, str):
                        return dt_to_unix_nanos(datetime.fromisoformat(val.replace("Z", "")))
                except Exception:
                    return None
                return None

            bars = self._catalog.bars(
                bar_types=[f"{instrument_id}-1-DAY-LAST-EXTERNAL"],
                start=_to_ns(start),
                end=_to_ns(end),
                as_nautilus=False,
            )
            if bars:
                return [float(b.close) for b in bars]
        except Exception:  # pylint: disable=broad-except
            pass

        return self._synthetic_prices(instrument_id)

    # ------------------------------------------------------------------
    @staticmethod
    def _synthetic_prices(instrument_id: str) -> List[float]:
        base = sum(ord(ch) for ch in instrument_id) % 100 + 50
        length = 40
        return [float(base + i) for i in range(length)]

    def get_instrument(self, instrument_id: str):  # noqa: D401
        if self._catalog is None:
            return {"id": instrument_id}
        try:
            ins = self._catalog.instruments(instrument_ids=[instrument_id], as_nautilus=False)
            if ins:
                return ins[0]
        except Exception:
            pass
        return {"id": instrument_id}

    # ------------------------------------------------------------------
    def get_all_instrument_ids(self):  # noqa: D401
        """Return list of all instrument IDs present in catalog or fallback."""
        if self._catalog is not None:
            try:
                return [str(ins.id) for ins in self._catalog.instruments()]
            except Exception:  # pylint: disable=broad-except
                pass
        # Synthetic fallback list
        return ["AAA.FUT.NSE", "BBB.FUT.NSE"]


__all__ = ["DataManager"] 