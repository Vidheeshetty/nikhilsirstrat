"""Integration test: verify Zerodha live tick stream for CRUDEOIL FUT contains OI.

The test needs valid Kite credentials via environment variables:
    - KITE_API_KEY
    - KITE_ACCESS_TOKEN (daily session token)

If the credentials are not supplied the test is skipped.

The test will:
1. Pull the MCX instrument dump.
2. Pick the nearest-expiry CRUDEOIL future (regular lot) symbol.
3. Start a KiteTicker WebSocket in FULL mode.
4. Wait up to 10 seconds to receive at least one tick that contains the
   `oi` field.

NOTE: This is purposely kept short-lived so that the test does not hang
CI pipelines lacking streaming access. It will auto-skip without creds.
"""

from __future__ import annotations

import os
import re
import threading
from time import sleep

import pytest

try:
    from kiteconnect import KiteConnect, KiteTicker  # type: ignore
except ImportError:  # pragma: no cover – dependency may be optional
    KiteConnect = None  # type: ignore
    KiteTicker = None  # type: ignore


@pytest.mark.integration
@pytest.mark.skipif(
    KiteConnect is None or KiteTicker is None,
    reason="kiteconnect package not installed",
)
def test_crudeoil_live_stream_contains_oi() -> None:  # noqa: D401
    """Assert that live ticks for CRUDEOIL FUT include the `oi` field."""

    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    # Fallback: load from YAML config if env vars missing
    if not (api_key and access_token):
        import yaml
        from pathlib import Path

        possible_cfgs = [
            Path("config/my_zerodha.yaml"),
            Path("config/paper_trading/my_zerodha.yaml"),
        ]
        cfg_file = next((p for p in possible_cfgs if p.exists()), None)
        if cfg_file:
            with cfg_file.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            broker_cfg = cfg.get("broker", {})
            api_key = broker_cfg.get("api_key", api_key)
            access_token = broker_cfg.get("access_token", access_token)

    if not api_key or not access_token:
        pytest.skip(
            "Kite credentials not provided via env vars or config YAML – skipping live test"
        )

    # ------------------------------------------------------------------
    # Step-1: discover the nearest CRUDEOIL future
    # ------------------------------------------------------------------
    kite = KiteConnect(api_key)
    kite.set_access_token(access_token)

    instruments = kite.instruments("MCX")  # MCX is the exchange, not instrument
    crude_contracts = [
        inst
        for inst in instruments
        if re.fullmatch(r"CRUDEOIL\d{2}[A-Z]{3}FUT", inst["tradingsymbol"])
    ]
    assert crude_contracts, "No CRUDEOIL futures found in instrument dump"

    # Sort by soonest expiry so we always pick the front-month contract
    crude_contracts.sort(key=lambda x: x["expiry"])
    instrument_token = crude_contracts[0]["instrument_token"]

    # ------------------------------------------------------------------
    # Step-2: spin up WebSocket & capture a tick with OI
    # ------------------------------------------------------------------
    ticker = KiteTicker(api_key, access_token)
    stopped = threading.Event()
    tick_data: dict[str, int] = {}

    def on_ticks(ws, ticks):  # pylint: disable=unused-argument
        for tick in ticks:
            if tick.get("instrument_token") == instrument_token and "oi" in tick:
                tick_data["oi"] = tick["oi"]
                stopped.set()

    def on_connect(ws, _response):  # pylint: disable=unused-argument
        ws.subscribe([instrument_token])
        ws.set_mode(ws.MODE_FULL, [instrument_token])  # FULL mode ⇒ includes OI

    def on_error(_ws, code, reason):  # noqa: D401
        pytest.fail(f"WebSocket error {code}: {reason}")

    ticker.on_ticks = on_ticks
    ticker.on_connect = on_connect
    ticker.on_error = on_error

    ticker.connect(threaded=True)

    # Wait max 10 s for the first suitable tick
    for _ in range(100):
        if stopped.wait(timeout=0.1):
            break
        sleep(0.1)

    # Clean shutdown
    try:
        ticker.close()
    except Exception:  # pragma: no cover – defensive cleanup
        pass

    assert "oi" in tick_data, "Did not receive a tick containing OI within 10 seconds"
