#!/usr/bin/env python3
"""Data Manager for TrendRidingStrategy Backtesting.

Loads daily Bars (and QuoteTicks if available) from a parquet catalog and
provides helper methods for synthetic tick creation, instrument resolution,
and macOS resource-fork cleanup.

This implementation is copied from *trend_follow_futures* with only minor
renaming.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Any

from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.data import QuoteTick, Bar
from nautilus_trader.model.objects import Price, Quantity


class DataManager:
    def __init__(self, catalog_path: str | None = None):
        if catalog_path is None:
            catalog_path = "catalog-data/trend_riding_strategy/catalog"
        self.catalog_path = catalog_path
        self._cleanup_resource_forks()
        self.catalog = ParquetDataCatalog(str(catalog_path))

    # ------------------------------------------------------------------
    # House-keeping helpers
    # ------------------------------------------------------------------
    def _cleanup_resource_forks(self) -> None:
        """Delete macOS '._' files which break Arrow reader."""
        removed = 0
        for p in Path(self.catalog_path).rglob("._*.parquet"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        if removed:
            print(f"DataManager: removed {removed} macOS resource-fork files from catalog")

    # ------------------------------------------------------------------
    # Instrument helpers
    # ------------------------------------------------------------------
    def get_instrument(self, instrument_id: str):
        """Return Nautilus Instrument; fallback for continuous/closest contracts."""
        insts = self.catalog.instruments(instrument_ids=[instrument_id], as_nautilus=True)
        if insts:
            return insts[0]

        # Fallbacks for FUT continuous symbol logic ----------------------
        if ".FUT." in instrument_id:
            base_symbol_with_expiry, _, venue = instrument_id.partition(".FUT.")
            import re
            base_symbol = re.sub(r"\d+$", "", base_symbol_with_expiry)

            # Continuous symbol requested (no expiry digits)
            if base_symbol == base_symbol_with_expiry:
                cands = [
                    ins for ins in self.catalog.instruments(as_nautilus=True)
                    if ins.raw_symbol.value.startswith(base_symbol) and ins.id.value.endswith(f".FUT.{venue}")
                ]
                if cands:
                    cands.sort(key=lambda ins: ins.expiration_ns)
                    return cands[0]

            # Concrete symbol missing – try continuous
            continuous_id = f"{base_symbol}.FUT.{venue}"
            insts_c = self.catalog.instruments(instrument_ids=[continuous_id], as_nautilus=True)
            if insts_c:
                return insts_c[0]
        raise ValueError(f"Instrument not found: {instrument_id}")

    # ------------------------------------------------------------------
    def _resolve_instrument_ids(self, instrument_id: str) -> List[str]:
        """Resolve continuous to concrete IDs for data loading."""
        all_ids = {ins.id.value for ins in self.catalog.instruments()}
        if instrument_id in all_ids:
            return [instrument_id]
        if ".FUT." in instrument_id and not any(ch.isdigit() for ch in instrument_id.split(".")[0]):
            base, _, venue = instrument_id.partition(".FUT.")
            return [
                ins.id.value for ins in self.catalog.instruments()
                if ins.raw_symbol.value.startswith(base) and ins.id.value.endswith(f".FUT.{venue}")
            ]
        # concrete missing -> try continuous fallback
        if ".FUT." in instrument_id:
            base_exp, _, venue = instrument_id.partition(".FUT.")
            import re
            base = re.sub(r"\d+$", "", base_exp)
            continuous_id = f"{base}.FUT.{venue}"
            if continuous_id in all_ids:
                return [continuous_id]
        return []

    # ------------------------------------------------------------------
    # Bar / Tick helpers
    # ------------------------------------------------------------------
    def get_bars(self, instrument_id: str, start, end) -> List[Bar]:
        from datetime import datetime
        from nautilus_trader.core.datetime import dt_to_unix_nanos

        def _to_ns(val):
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                dt = datetime.fromisoformat(val.replace("Z", ""))
                return dt_to_unix_nanos(dt)
            raise TypeError("start/end must be int ns or ISO string")

        start_ns = _to_ns(start)
        end_ns = _to_ns(end)
        ids = self._resolve_instrument_ids(instrument_id)
        bars: list[Bar] = []
        BAR_INTERVAL = "1-DAY"
        for iid in ids:
            bar_type = f"{iid}-{BAR_INTERVAL}-LAST-EXTERNAL"
            try:
                chunk = self.catalog.bars(bar_types=[bar_type], start=start_ns, end=end_ns, as_nautilus=True)
                bars.extend(chunk)
            except Exception as e:
                print(f"[WARN] Failed loading bars for {iid}: {e}")
        return sorted(bars, key=lambda b: b.ts_event)

    def get_quote_ticks(self, instrument_id: str, start: str, end: str) -> List[QuoteTick]:
        # Try real ticks first
        try:
            qts = self.catalog.quote_ticks(instrument_ids=[instrument_id], start=start, end=end, as_nautilus=True)
            if qts:
                return qts
        except Exception:
            pass
        # Otherwise synthesize from bars
        bars = self.get_bars(instrument_id, start, end)
        qts: List[QuoteTick] = []
        for bar in bars:
            inst_id = bar.bar_type.instrument_id if hasattr(bar.bar_type, "instrument_id") else InstrumentId.from_str(instrument_id)
            qt = QuoteTick(
                instrument_id=inst_id,
                ts_event=bar.ts_event,
                ts_init=bar.ts_init,
                bid_price=Price(bar.close.as_double(), bar.close.precision),
                ask_price=Price(bar.close.as_double(), bar.close.precision),
                bid_size=Quantity(bar.volume.as_double(), bar.volume.precision),
                ask_size=Quantity(bar.volume.as_double(), bar.volume.precision),
            )
            qts.append(qt)
        return qts

    # ------------------------------------------------------------------
    def validate_instrument_data(self, instrument_id: str, start: str, end: str) -> bool:
        return bool(self.get_bars(instrument_id, start, end))

    def get_all_instrument_ids(self) -> List[str]:
        """Return all instrument IDs present in the catalog."""
        return sorted({str(ins.id) for ins in self.catalog.instruments()}) 