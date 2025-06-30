# Reporting Architecture

This document captures the design of the *runlogs* reporting subsystem that supersedes the old `_summary.txts` pipeline.

---
## 1. Directory Layout
```
runlogs/
├── individual/
│   └── YYYY-MM-DD_HH-MM-SS/  # one folder per run
│       ├── <instrument>.html  # candlesticks, equity curve, trade table
│       └── ...
└── batch/
    └── YYYY-MM-DD_HH-MM-SS/
        ├── summary.html        # dashboard across instruments
        ├── trade_details.csv   # flat table for Excel/BI
        ├── trade_details.json  # same data for code
        └── assets/             # plotly.min.js, report.css (copied once per run)
```

*One run* always produces exactly one timestamped folder under **individual/** *and* one under **batch/**.

---
## 2. Dependencies
* Python ≥3.10
* nautilus-trader ≥1.116 (provides `BacktestEngine`, `BacktestResult`, `Trade`, etc.)
* pandas (CSV writing)
* Jinja2 (HTML templating)
* plotly.js (bundled via CDN)

> ⚠️ There is **no fallback** for environments without Nautilus–Trader; the platform is designed exclusively for Nautilus data-models.

---
## 3. Model-View-Controller Overview

### Model  
We reuse Nautilus objects directly:
* **BacktestResult** – per-instrument result (positions, trades, metrics).
* **Trade** – individual trade with PnL, exit reason, etc.

### View  
Renderers convert Nautilus objects into artefacts.
* `HtmlInstrumentRenderer`
* `HtmlBatchRenderer`
* `CsvTradeRenderer`
* `JsonTradeRenderer`

Templates live in `utils/reporting/templates/*.j2`.

### Controller  
`ReportController.generate(out_dir, results)`
1. Creates timestamped sub-dirs.
2. Delegates to each renderer.
3. Copies static assets.

---
## 4. Trade Table Schema
| Column            | Source                     |
|-------------------|----------------------------|
| instrument_id     | `Trade.instrument_id`      |
| entry_ts          | `Trade.entry_ts`           |
| exit_ts           | `Trade.exit_ts`            |
| side              | `Trade.side`               |
| exit_reason       | `Trade.exit_reason`        |
| entry_price       | `Trade.entry_price`        |
| exit_price        | `Trade.exit_price`         |
| realised_pnl      | `Trade.pnl`                |
| return_pct        | computed                   |
| trigger_entry     | strategy-provided string   |
| trigger_exit      | strategy-provided string   |
| iv                | meta field (if present)    |
| oi                | meta field (if present)    |

---
## 5. HTML Features
* Plotly candlestick with SMA/EMA overlays.
* Equity curve and draw-down charts.
* Sortable tables via *tablesort.js*.
* Responsive single-file reports (works offline).

---
## 6. Extending
* Add a new indicator overlay → update Jinja2 template to pull extra series from embedded JSON.
* Additional export formats → implement another `Renderer` subclass.
* Strategy-specific columns → emit them in `Trade.meta`, renderer auto-includes unknown keys.

---
## 7. Future Work
* CLI flag `--no-html` to skip heavy renderers for CI.
* PDF export via `weasyprint`.
* Open-high-low-close volume bars once volume is populated. 