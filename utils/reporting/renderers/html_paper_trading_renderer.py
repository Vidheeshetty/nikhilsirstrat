from __future__ import annotations

"""HTML renderer for paper-trading sessions (minimal stub).

This lightweight implementation keeps the FastAPI dashboard functional until a
full-featured template-driven renderer is added.  It writes very simple HTML so
that callers don't crash.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

__all__ = ["HTMLPaperTradingRenderer"]


class HTMLPaperTradingRenderer:  # pylint: disable=too-few-public-methods
    async def initialize(self, session_dir: Path):  # noqa: D401
        """Called once at reporter start – create static asset folders here."""
        self._session_dir = Path(session_dir)
        self._session_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    async def render_live_dashboard(self, snapshot: Dict[str, Any], session_data):  # noqa: D401
        """Return a simple live dashboard HTML string."""
        ts = snapshot.get("timestamp", datetime.utcnow())
        metrics = snapshot.get("metrics", {})
        body_lines = [f"<h1>Live Dashboard – {ts}</h1>"]
        if metrics:
            body_lines.append("<h2>Key Metrics</h2><ul>")
            for k, v in metrics.items():
                body_lines.append(f"<li><b>{k}:</b> {v}</li>")
            body_lines.append("</ul>")
        return "<html><body>" + "\n".join(body_lines) + "</body></html>"

    # ------------------------------------------------------------------
    async def render_full_report(self, session_data, final_metrics):  # noqa: D401
        """Return an end-of-day static report."""
        lines = [
            "<html><body>",
            f"<h1>Paper Trading Report – Session {session_data.get('start_time')}</h1>",
            "<h2>Final Metrics</h2>",
            "<ul>",
        ]
        for k, v in final_metrics.items():
            lines.append(f"<li><b>{k}:</b> {v}</li>")
        lines.extend(["</ul>", "</body></html>"])
        return "\n".join(lines) 