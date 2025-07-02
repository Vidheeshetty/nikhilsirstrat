from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd
import numbers

from .base import Renderer
from utils.reporting.metrics import enrich_trades

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\"/>
  <title>Batch Back-test Summary</title>
  <link rel=\"stylesheet\" href=\"assets/report.css\"/>
  <script src=\"https://cdn.plot.ly/plotly-2.27.0.min.js\"></script>
</head>
<body>
<h1>Batch Back-test Summary</h1>
<p>Generated at {{timestamp}}</p>

<h2>Run Info</h2>
<table class="table">
  <tbody>
    <tr><td>Strategy</td><td>{{strategy_name}}</td></tr>
    <tr><td>Period</td><td>{{period}}</td></tr>
    <tr><td>Data Source</td><td>{{data_source}}</td></tr>
    {{config_row}}
  </tbody>
</table>

<h2>Portfolio KPIs</h2>
<table class="table">
  <tbody>
    <tr><td>Realised PnL</td><td>{{total_pnl}}</td></tr>
    <tr><td>Realised PnL %</td><td>{{total_pnl_pct}}</td></tr>
    <tr><td>Total Investment</td><td>{{total_investment}}</td></tr>
    <tr><td>Total Orders</td><td>{{total_orders}}</td></tr>
    <tr><td>Total Positions</td><td>{{total_positions}}</td></tr>
    <tr><td>Total Trades</td><td>{{total_trades}}</td></tr>
    <tr><td>Profitable Trades</td><td>{{profitable_trades}}</td></tr>
    <tr><td>Losing Trades</td><td>{{losing_trades}}</td></tr>
    <tr><td>Max Drawdown %</td><td>{{max_drawdown}}</td></tr>
    <tr><td>Unrealised PnL</td><td>{{unrealised_pnl}}</td></tr>
    <tr><td>Starting Balance</td><td>{{starting_balance}}</td></tr>
    <tr><td>Ending Balance</td><td>{{ending_balance}}</td></tr>
    <tr><td>Free Balance</td><td>{{free_balance}}</td></tr>
    <tr><td>Locked Balance</td><td>{{locked_balance}}</td></tr>
    <tr><td>Avg Sharpe</td><td>{{avg_sharpe}}</td></tr>
    <tr><td>Win Rate</td><td>{{win_rate}}</td></tr>
  </tbody>
</table>

<h2>Instrument Leaderboard</h2>
<table class=\"table\">
  <thead><tr><th>Instrument</th><th>PnL</th><th>Sharpe</th></tr></thead>
  <tbody>
  {{rows}}
  </tbody>
</table>

<h2>PnL Bar Chart</h2>
<div id=\"pnl_bar\"></div>
<script>
const data = {{plot_data}};
Plotly.newPlot('pnl_bar', data, {margin:{t:20}});
</script>

<h2>Trade Details</h2>
<table class=\"table\">
  <thead>
    <tr>{{trade_header}}</tr>
  </thead>
  <tbody>
    {{trade_rows}}
  </tbody>
</table>

<h2>Indicator Chart</h2>
{{indicator_iframe}}
</body></html>"""


# ------------------------------------------------------------------
# Helper for currency formatting (INR symbol by default) -------------
# ------------------------------------------------------------------


def fmt_money(value: float | int, symbol: str = "₹") -> str:
    """Return the value formatted as currency with thousands separator.

    Examples:
    >>> fmt_money(605641.7)
    '₹605,641.70'
    >>> fmt_money(-1500)
    '₹-1,500.00'
    """
    try:
        return f"{symbol}{value:,.2f}"
    except Exception:  # pragma: no cover – defensive fallback
        return f"{symbol}{value}"


class HtmlBatchRenderer(Renderer):
    def render(
        self,
        results: list[dict],
        outfile: str | Path,
        *,
        strategy_name: str | None = None,
    ) -> None:  # noqa: D401
        # -------------------- AGGREGATE METRICS ---------------------------
        total_pnl = sum(r.get("pnl", 0.0) for r in results)

        # ------------- Flatten & enrich trade-level data ----------------
        trade_rows_raw = [t for r in results for t in r.get("trades", [])]
        trade_df = pd.DataFrame(trade_rows_raw)

        # ------------------------------------------------------------------
        # Fallback – synthesize *basic* trade rows from summary metrics so
        # that the Trade Details table in HTML is never empty. This covers
        # legacy runners that don't supply ``trades`` in their result dicts.
        # ------------------------------------------------------------------
        if trade_df.empty:
            synthetic_rows = []
            for r in results:
                instrument = r.get("instrument_id", "UNKNOWN")
                entry_price = r.get("entry_price") or (
                    r.get("prices")[0] if r.get("prices") else None
                )  # type: ignore[index]
                exit_price = r.get("exit_price") or (
                    r.get("prices")[-1] if r.get("prices") else None
                )  # type: ignore[index]
                if entry_price is None or exit_price is None:
                    # Fabricate prices using pnl if available --------------------------------
                    pnl = r.get("pnl", 0.0)
                    entry_price = 100.0  # arbitrary base
                    exit_price = entry_price + pnl

                realised_pnl = exit_price - entry_price
                pnl_pct = (realised_pnl / entry_price) * 100 if entry_price else 0.0

                synthetic_rows.append(
                    {
                        "Instrument": instrument,
                        "Entry_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Trade_Type": "Long" if realised_pnl >= 0 else "Short",
                        "Exit_Reason": "Synthetic",
                        "Entry_Price": round(entry_price, 2),
                        "IV": round(entry_price * 0.25, 2),
                        "OI": int(entry_price * 10),
                        "Exit_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Exit_Price": round(exit_price, 2),
                        "Threshold": round(entry_price * 0.02, 2),
                        "SL_Price": round(entry_price * 0.98, 2),
                        "Realised_PnL": round(realised_pnl, 2),
                        "PnL%": round(pnl_pct, 2),
                        "Sharpe": round(r.get("sharpe", 0.0), 2),
                        "Cum_PnL": None,
                    }
                )

            trade_df = pd.DataFrame(synthetic_rows)

        # Enrich calculated fields (Cum_PnL, is_win, etc.) ------------------
        if not trade_df.empty:
            trade_df = enrich_trades(trade_df)

        # Remove technical helper columns that aren't useful in the HTML table
        if "is_win" in trade_df.columns:
            trade_df = trade_df.drop(columns=["is_win"])  # keep Win/Loss only

        total_trades = len(trade_df)
        if "Win/Loss" in trade_df.columns:
            profitable_trades = (trade_df["Win/Loss"] == "Win").sum()
            losing_trades = (trade_df["Win/Loss"] == "Loss").sum()
        else:
            profitable_trades = losing_trades = 0

        win_rate = (
            f"{(profitable_trades / total_trades * 100):.2f}%"
            if total_trades
            else "N/A"
        )

        # Use peak exposure (max entry price / leverage) instead of naive sum
        peak_exposure = (
            max(r.get("peak_exposure", 0.0) for r in results) if results else 0.0
        )
        total_investment = peak_exposure
        total_pnl_pct = (
            f"{(total_pnl / peak_exposure * 100):.2f}%" if peak_exposure else "N/A"
        )

        # Drop unnecessary columns ------------------------------------------------
        for col in ("Threshold", "SL_Price"):
            if col in trade_df.columns:
                trade_df = trade_df.drop(columns=[col])

        total_orders = total_trades * 2
        total_positions = total_trades

        max_drawdown = (
            max(r.get("mdd_pct", r.get("max_drawdown_pct", 0.0)) for r in results)
            if results
            else 0.0
        )

        unrealised_pnl = 0.0  # placeholder until live PnL tracking added
        starting_balance = total_investment
        ending_balance = starting_balance + total_pnl
        free_balance = ending_balance
        locked_balance = 0.0

        avg_sharpe = (
            sum(r.get("sharpe", 0.0) for r in results) / len(results)
            if results
            else 0.0
        )

        # ------------------------------------------------------------------
        # Derive *period* and *data source* heuristically -------------------
        # ------------------------------------------------------------------
        # Instead of relying on trade date formats, get the actual data period
        # from the catalog or environment
        if results and results[0].get("start_time") and results[0].get("end_time"):
            from datetime import datetime as _dt

            s = _dt.utcfromtimestamp(results[0]["start_time"] / 1_000_000_000).strftime(
                "%Y-%m-%d"
            )
            e = _dt.utcfromtimestamp(results[0]["end_time"] / 1_000_000_000).strftime(
                "%Y-%m-%d"
            )
            period = f"{s} → {e}"
        else:
            period = self._get_data_period()

        # ------------------------------------------------------------------
        # Determine data source – prefer explicit value from runner results.
        # If multiple instruments disagree we pick the first non-null one.
        # ------------------------------------------------------------------
        data_source = next(
            (r.get("data_source") for r in results if r.get("data_source")), None
        )
        if not data_source:
            data_source = "Daily bars (synthetic)"

        # --------------------- LEADERBOARD ROWS ---------------------------
        row_html = "\n".join(
            f"<tr><td>{r['instrument_id']}</td><td>{fmt_money(r.get('pnl', 0))}</td><td>{r.get('sharpe', 0):.2f}</td></tr>"
            for r in sorted(results, key=lambda x: x.get("pnl", 0.0), reverse=True)
        )

        # Plotly data -------------------------------------------------------
        # Round PnL values to 2 decimals for cleaner JSON embedding
        plot_data = [
            {
                "type": "bar",
                "x": [r["instrument_id"] for r in results],
                "y": [round(float(r.get("pnl", 0.0)), 2) for r in results],
                "marker": {"color": "#4a90e2"},
            }
        ]

        # --------------------- TRADE DETAILS TABLE ------------------------
        if not trade_df.empty:
            header_cells = [f"<th>{col}</th>" for col in trade_df.columns]
            body_rows = []
            for _, tr in trade_df.iterrows():

                def _fmt(val):
                    if isinstance(val, numbers.Number):
                        return f"{val:.2f}"
                    return val

                body_rows.append(
                    "<tr>"
                    + "".join(f"<td>{_fmt(tr[col])}</td>" for col in trade_df.columns)
                    + "</tr>"
                )
            trade_header_html = "".join(header_cells)
            trade_rows_html = "\n".join(body_rows)
        else:
            trade_header_html = ""
            trade_rows_html = "<tr><td colspan='3'>No trade data available</td></tr>"

        # --------------------- CONFIG PARAMS ROW ----------------------
        config_row = ""
        try:
            import yaml  # type: ignore

            if strategy_name:
                yaml_path = Path(f"src/strategies/{strategy_name}/strategy.yaml")
                if yaml_path.exists():
                    cfg_dict = yaml.safe_load(yaml_path.read_text()) or {}
                    # Select key params in desired order
                    param_keys = [
                        "use_sma",
                        "use_fractals",
                        "sma_short_period",
                        "sma_long_period",
                        "risk_per_trade",
                    ]
                    cells = "".join(
                        f"<td><strong>{k}</strong></td><td>{cfg_dict.get(k, 'N/A')}</td>"
                        for k in param_keys
                    )
                    if cells:
                        config_row = f"<tr>{cells}</tr>"
        except Exception:
            # Silently ignore YAML parsing issues
            config_row = ""

        # --------------------- FINAL RENDER -------------------------------
        plot_path = next(
            (r.get("plot_path") for r in results if r.get("plot_path")), None
        )
        indicator_iframe = (
            f'<iframe src="{plot_path}" width="100%" height="600" style="border:none;"></iframe>'
            if plot_path
            else "<p>Indicator chart not available</p>"
        )
        html = (
            HTML_TEMPLATE.replace(
                "{{timestamp}}", datetime.now().isoformat(sep=" ", timespec="seconds")
            )
            .replace("{{strategy_name}}", strategy_name or "Unknown")
            .replace("{{period}}", period)
            .replace("{{data_source}}", data_source)
            .replace("{{total_pnl}}", fmt_money(total_pnl))
            .replace("{{total_pnl_pct}}", total_pnl_pct)
            .replace("{{total_investment}}", fmt_money(total_investment))
            .replace("{{total_orders}}", str(total_orders))
            .replace("{{total_positions}}", str(total_positions))
            .replace("{{total_trades}}", str(total_trades))
            .replace("{{profitable_trades}}", str(profitable_trades))
            .replace("{{losing_trades}}", str(losing_trades))
            .replace("{{max_drawdown}}", f"{max_drawdown:.2f}%")
            .replace("{{unrealised_pnl}}", fmt_money(unrealised_pnl))
            .replace("{{starting_balance}}", fmt_money(starting_balance))
            .replace("{{ending_balance}}", fmt_money(ending_balance))
            .replace("{{free_balance}}", fmt_money(free_balance))
            .replace("{{locked_balance}}", fmt_money(locked_balance))
            .replace("{{avg_sharpe}}", f"{avg_sharpe:.2f}")
            .replace("{{win_rate}}", win_rate)
            .replace("{{rows}}", row_html)
            .replace("{{plot_data}}", str(plot_data))
            .replace("{{trade_header}}", trade_header_html)
            .replace("{{trade_rows}}", trade_rows_html)
            .replace("{{config_row}}", config_row)
            .replace("{{indicator_iframe}}", indicator_iframe)
        )
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Helper methods ---------------------------------------------------
    # ------------------------------------------------------------------

    def _get_data_period(self) -> str:
        """Get the actual data period from the catalog if available."""
        import os

        try:
            # Try to get the catalog path from environment
            catalog_path = os.environ.get("DATA_CATALOG_ROOTS")
            if not catalog_path:
                return "N/A"

            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
            from nautilus_trader.core.datetime import unix_nanos_to_dt

            cat = ParquetDataCatalog(catalog_path)
            interval = os.environ.get("BAR_INTERVAL", "1-DAY").upper()
            instruments = cat.instruments()
            if not instruments:
                return "N/A"

            all_dates = []
            for instrument in instruments:
                bars = cat.bars(
                    bar_types=[f"{instrument.id}-{interval}-LAST-EXTERNAL"],
                    as_nautilus=False,
                )
                if bars:
                    for bar in bars:
                        date = unix_nanos_to_dt(bar.ts_event)
                        all_dates.append(date.strftime("%Y-%m-%d"))

            if all_dates:
                unique_dates = sorted(set(all_dates))
                return f"{unique_dates[0]} → {unique_dates[-1]}"
            else:
                return "N/A"

        except Exception:  # pragma: no cover
            return "N/A"


__all__ = ["HtmlBatchRenderer"]
