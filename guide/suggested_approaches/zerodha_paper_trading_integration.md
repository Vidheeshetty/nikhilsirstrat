# Zerodha Paper-Trading Integration – Suggested Approach

> **Audience**: Developers / DevOps deploying NTbasedPlatform on a box that should trade via Zerodha in *paper* mode.
>
> **Goal**: Provide a single, opinionated recipe that supports **both**:
> 1. Instant, deterministic fills via the in-house simulator (great for CI & back-fills)
> 2. Realistic order-ack flow via Zerodha's live API / sandbox (great for latency & margin checks)

---
## 1  Architecture at a Glance

```text
┌──────────────────┐          ┌──────────────────────────┐
│ TrendRiding ...  │  orders  │ ZerodhaBroker (wrapper)  │────────┐
├──────────────────┤────────▶ │  ↳ mode: simulator/API   │        │
│ SwingRange ...   │          └──────────────────────────┘        │
└──────────────────┘                         │ fills / rejections │
                                            ▼                     ▼
                                ┌──────────────────┐  Web-Socket  │
                                │  KiteConnect     │◀─────────────┘
                                └──────────────────┘
```

* **`ZerodhaBroker`** contains *both* behaviours. At runtime it inspects the `paper_trading:` flag in YAML:
  * `true`  → routes orders to the in-process simulator (zero latency, CSV-replay friendly)
  * `false` → forwards to real KiteConnect endpoints (requires valid API key / token)

---
## 2  YAML Examples

### 2.1  In-House Simulator (CI / local dry-run)
```yaml
# config/paper_trading/zerodha_sim.yaml
broker:
  type: ZerodhaBroker
  api_key: DUMMY
  api_secret: DUMMY
  access_token: DUMMY
  paper_trading: true           # ✨ simulator mode

feed:
  source: csv_replay            # replays historical CSV files
  csv_dir: data/nse/
  bar_type: 1MIN
update_frequency: 1             # seconds
```

### 2.2  Real Zerodha API (pre-prod soak)
```yaml
# config/paper_trading/zerodha_api.yaml
broker:
  type: ZerodhaBroker
  api_key: "{{ secrets.KITE_KEY }}"
  api_secret: "{{ secrets.KITE_SECRET }}"
  access_token: "{{ runtime.KITE_AT }}"
  paper_trading: false          # ✨ API mode
  product_type: MIS             # CNC / MIS / NRML
  retry_on_rate_limit: true
  max_retries: 3

feed:
  source: live_ws               # Zerodha live ticks
  bar_type: TICK
```

---
## 3  Running in Parallel

```bash
# Terminal 1 – deterministic simulator
python scripts/run_paper_trading.py \
       --config config/paper_trading/zerodha_sim.yaml

# Terminal 2 – API latency test (same strategies)
python scripts/run_paper_trading.py \
       --config config/paper_trading/zerodha_api.yaml
```
Each process writes to its own timestamped folder under `runlogs/papertrading/`. Compare PnL & fill-times to validate behaviour.

---
## 4  Recommended Workflow

| Phase | Purpose | Config | Notes |
|-------|---------|--------|-------|
| **Unit / Integration** | CI tests, deterministic | `paper_trading: true`, `csv_replay` | Fast, offline |
| **Local Dry-Run** | Developer sanity check | same as above | |
| **Broker Smoke-Test** | Validate creds, rate-limits | `paper_trading: false`, tiny qty | Use `MIS` + 1-lot NIFTY |
| **Pre-Prod Soak** | 24-h comparison | run *both* configs side-by-side | Alert on drift |
| **Production** | Real capital | switch to `live_runner.py` or keep API mode but `product_type: CNC` | |

---
## 5  Caveats & Tips

1. **Rate limits** – Zerodha is 3 requests/sec; the wrapper has a token-bucket (`max_requests_per_sec`).
2. **Margins** – Sandbox still checks margins; adjust `risk_management.global_max_positions`.
3. **Clock skew** – Enable NTP; timestamp mismatches break tick alignment.
4. **PnL drift** – Simulator fills at midpoint; API fills at exchange; expect small delta.
5. **Credentials separation** – Keep **dummy** creds under VCS; inject real keys via env-vars / CI secrets.

---
## 6  Implementation Checklist

1. Place both YAMLs under `config/paper_trading/`.
2. Populate `.env` or secret store with live API keys for the API mode.
3. Start services (systemd / tmux):
   ```bash
   # simulator service
   python scripts/run_paper_trading.py --config config/paper_trading/zerodha_sim.yaml &
   # API service
   python scripts/run_paper_trading.py --config config/paper_trading/zerodha_api.yaml &
   ```
4. Tail logs in `runlogs/papertrading/` or via dashboard.

> **Done!** You can toggle modes or run both simultaneously with just YAML changes – no code edits required.

---
## 7. Optional Enhancements

* **Nautilus-Trader object mapping** – wrap `_kite_to_nautilus_order()` & `_kite_to_nautilus_trade()` in `client.py` to feed directly into Nautilus back-end models.
* **Latency histogram** – record `order_send_ts` vs `exchange_ack_ts` and plot in the dashboard.
* **Risk matrix** – VaR & exposure heat-map per instrument.
* **SSL termination** – add Let's Encrypt in the Nginx config for secure remote access.

---
## 8  Switching to Real Money (Live-Capital Trading)

> Skip this entire step if you intend to stay in the **paper** / sandbox environment.

1. Change `paper_trading: false` in the YAML you deploy.  
2. Use API credentials created under a **live** Kite Connect app (production endpoint).  
3. Review / lower risk limits (`risk_management.*`).  
4. Hard-wire MFA on the server, rotate tokens daily, enable IP whitelisting.

Once those four items are in place the very same broker wrapper starts routing to the exchange and the reporting stack behaves identically – only now with real capital.

---
## 9  About Zerodha's "official" paper-trading options

Zerodha itself **does not** offer a first-class paper-trading API.  The usual options are:

| Option | What it really is | Pros | Cons |
|--------|-------------------|------|------|
| **Kite "Sandbox" keys** | You get a second API key whose orders are rejected at OMS but still return order-ids | Same request/response format; rate-limits identical | No fills → you still need a simulator for P&L & positions |
| **Small-quantity MIS orders** | Place ₹1 or 1-share orders on real exchange (intraday) | True exchange latencies & margin checks | Non-zero cost; clutter in console; not risk-free |
| **Third-party mock OMS** | Community projects that mimic Kite | Free & offline | Not maintained / diverge from real API |

Therefore NTbasedPlatform keeps an **internal simulator** (accurate fills, deterministic back-replay) and can optionally hit the real Kite endpoints when you want latency realism.  If Zerodha ever releases a fully-featured paper OMS the broker wrapper can switch to that with minimal effort – open TODO in `zerodha/broker.py`. 