from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .base import Renderer

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
<div class=\"kpi\">Total PnL: {{total_pnl}}</div>
<div class=\"kpi\">Avg Sharpe: {{avg_sharpe}}</div>

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
</body></html>"""


class HtmlBatchRenderer(Renderer):
    def render(self, results: List[Dict[str, Any]], out_path: Path) -> None:  # noqa: D401
        total_pnl = sum(r.get("pnl", 0.0) for r in results)
        avg_sharpe = (
            sum(r.get("sharpe", 0.0) for r in results) / len(results) if results else 0.0
        )
        # Build rows
        row_html = "\n".join(
            f"<tr><td>{r['instrument_id']}</td><td>{r.get('pnl',0):.2f}</td><td>{r.get('sharpe',0):.2f}</td></tr>"
            for r in results
        )
        # Plotly data
        plot_data = [
            {
                "type": "bar",
                "x": [r["instrument_id"] for r in results],
                "y": [r.get("pnl", 0.0) for r in results],
                "marker": {"color": "#4a90e2"},
            }
        ]
        html = (
            HTML_TEMPLATE.replace("{{timestamp}}", datetime.now().isoformat(sep=" ", timespec="seconds"))
            .replace("{{total_pnl}}", f"{total_pnl:.2f}")
            .replace("{{avg_sharpe}}", f"{avg_sharpe:.2f}")
            .replace("{{rows}}", row_html)
            .replace("{{plot_data}}", str(plot_data))
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")


__all__ = ["HtmlBatchRenderer"] 