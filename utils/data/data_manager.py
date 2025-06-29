from __future__ import annotations

"""Data loading utilities for backtest runners.

Provides DataManager class that abstracts data access for strategies,
supporting both real Nautilus Parquet catalogs and synthetic test data.
"""

from typing import List
from pathlib import Path


class DataManager:  # pylint: disable=too-few-public-methods
    """Return price series; prefers real parquet catalog if available."""

    def __init__(self, catalog_path: str | None = None):
        """Initialise, optionally with *catalog_path* or env DATA_CATALOG_ROOTS.

        *catalog_path* may be a colon-separated list of roots.  Each root must
        contain ``catalog/`` and ``catalog-meta/`` sub-folders.
        """
        import os

        roots_raw = (
            catalog_path
            or os.environ.get("DATA_CATALOG_ROOTS")
            or "catalog-data/shared"
        )

        def _nearest_catalog_root(path: Path) -> Path:
            """Return the nearest ancestor that looks like a Parquet catalog root.

            A *catalog root* is defined as a directory which contains both
            ``catalog/`` and ``catalog-meta/`` sub-folders.  If no such parent is
            found within a reasonable number of ascents (5 levels), the original
            *path* is returned unchanged so that the subsequent ParquetDataCatalog
            instantiation can still attempt to use it directly.
            """

            current = path.expanduser().resolve()
            for _ in range(6):  # current + 5 parents
                if (current / "catalog").exists() and (
                    current / "catalog-meta"
                ).exists():
                    return current
                if current.parent == current:
                    break
                current = current.parent
            return path

        roots = [str(_nearest_catalog_root(Path(r))) for r in roots_raw.split(":")]

        # Remove potential duplicates after normalisation
        seen: set[str] = set()
        normalised_roots: list[str] = []
        for r in roots:
            rp = str(Path(r).resolve())
            if rp not in seen:
                normalised_roots.append(rp)
                seen.add(rp)

        self._catalogs = []
        for root in normalised_roots:
            try:
                from nautilus_trader.persistence.catalog.parquet import (
                    ParquetDataCatalog,
                )  # type: ignore

                cat = ParquetDataCatalog(root)
                # trigger a light query to confirm catalog is usable
                _ = cat.instruments(limit=1)  # type: ignore[attr-defined]
                self._catalogs.append(cat)
            except Exception:  # pylint: disable=broad-except
                continue  # skip unusable roots

    # ------------------------------------------------------------------
    # Private helper reused by both public getters
    # ------------------------------------------------------------------

    def _load_prices(
        self,
        instrument_id: str,
        start=None,
        end=None,
        *,
        allow_stub: bool = False,
    ) -> List[float]:  # noqa: D401
        """Return a list of close prices (floats).

        Parameters
        ----------
        allow_stub : bool, default False
            When *True* (used mainly in fast unit tests) the method returns a
            deterministic synthetic price series if the Parquet catalog is
            unavailable or does not contain enough bars for the requested
            instrument.  When *False* it raises ``ValueError`` instead so that
            production code never silently trades on mock data.
        """

        if not self._catalogs:
            if allow_stub:
                return self._synthetic_prices(instrument_id)
            raise ValueError(f"Catalog not available for instrument {instrument_id}")

        for cat in self._catalogs:
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
                            return dt_to_unix_nanos(
                                datetime.fromisoformat(val.replace("Z", ""))
                            )
                    except Exception:
                        return None
                    return None

                bars = cat.bars(
                    bar_types=[f"{instrument_id}-1-DAY-LAST-EXTERNAL"],
                    start=_to_ns(start),
                    end=_to_ns(end),
                    as_nautilus=False,
                )
                if bars and len(bars) > 1:
                    return [float(b.close) for b in bars]
            except Exception:  # pylint: disable=broad-except
                pass

        if allow_stub:
            return self._synthetic_prices(instrument_id)

        raise ValueError(f"No data found for instrument {instrument_id}")

    # ------------------------------------------------------------------
    @staticmethod
    def _synthetic_prices(instrument_id: str) -> List[float]:
        base = sum(ord(ch) for ch in instrument_id) % 100 + 50
        length = 40
        return [float(base + i) for i in range(length)]

    def get_instrument(self, instrument_id: str):  # noqa: D401
        if not self._catalogs:
            return {"id": instrument_id}
        try:
            for cat in self._catalogs:
                ins = cat.instruments(instrument_ids=[instrument_id], as_nautilus=False)
                if ins:
                    return ins[0]
        except Exception:
            pass
        return {"id": instrument_id}

    # ------------------------------------------------------------------
    def get_all_instrument_ids(self):  # noqa: D401
        """Return list of all instrument IDs present in catalog or fallback."""
        if not self._catalogs:
            return ["AAA.FUT.NSE", "BBB.FUT.NSE"]
        try:
            ids = []
            for cat in self._catalogs:
                ids.extend([str(ins.id) for ins in cat.instruments()])
            return ids
        except Exception:  # pylint: disable=broad-except
            pass
        # Synthetic fallback list
        return ["AAA.FUT.NSE", "BBB.FUT.NSE"]

    # ------------------------------------------------------------------
    # Public API – separates trade vs quote series (future-proof)
    # ------------------------------------------------------------------

    def get_trade_ticks(
        self, instrument_id: str, start=None, end=None, *, allow_stub: bool = False
    ) -> List[float]:  # noqa: D401
        """Return trade-level close prices (bars) used by back-tests."""
        return self._load_prices(instrument_id, start, end, allow_stub=allow_stub)

    def get_quote_ticks(
        self, instrument_id: str, start=None, end=None, *, allow_stub: bool = False
    ) -> List[float]:  # noqa: D401
        """Return quote-level prices (bars) used by back-tests."""
        return self._load_prices(instrument_id, start, end, allow_stub=allow_stub)

    # ------------------------------------------------------------------
    # Metadata helpers --------------------------------------------------
    # ------------------------------------------------------------------

    def describe_source(self) -> str:  # noqa: D401
        """Return a short label describing where price bars are loaded from."""
        return (
            "Daily bars (Parquet catalog: 1-DAY-LAST)"
            if self._catalogs
            else "Daily bars (synthetic)"
        )


__all__ = ["DataManager"]
