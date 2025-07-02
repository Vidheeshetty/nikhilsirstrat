# Cursor Learning Log

(MOVED from `docs/cursor_learning_log.md` on 2025-06-30)

| Date | Area | Lesson | Importance |
|------|------|--------|------------|
| 2025-06-30 | Strategy Runners | Exit logic must close **on opposite signal** as well as stop-loss; otherwise the back-test records only one trade.  Ensure position resets its trend-latch when trade closes. | High |
| 2025-06-30 | Imports / Scope | Prefer local imports *inside* functions only when required; otherwise add them at the top.  Two `UnboundLocalError`s (Path / datetime) slipped through due to redeclarations. | Med |
| 2025-06-30 | Reporting | Embed visual artefacts (Plotly HTML) directly in run-reports for rapid debugging; generates "see-it-once" feedback loop. | Low |

Guidelines
1. Keep each row ≤ 120 chars; link to commit hash if context is non-obvious.  
2. Upgrade *Importance* if the same mistake bites us twice (H → Critical).  
3. The `1dev_com.sh` gate parses **High** items and warns if patterns re-appear. 