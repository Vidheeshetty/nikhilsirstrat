# Test-Impact Matrix

This document lists which automated tests **must be re-executed** whenever a developer touches specific areas of the code-base.  It complements `.cursor/rules.md` by keeping the rules file concise while still providing a single source of truth.

| Code area modified | Affected test suites / commands |
|--------------------|---------------------------------|
| `utils/reporting/` (renderers, controller, metrics) | `pytest tests/system/test_report_system.py::test_trade_report_contents -m system` |
| Report directory layout logic (`ReportController.generate`, `.latest_report_dir`) | same as above |
| Trade enrichment helpers (`utils/reporting/metrics.py`) | `pytest tests/unit/test_metrics.py` + system test |
| Back-test runner orchestration (`utils/runners/*`, `strategies/*/runner/`) | `pytest tests/integration`, `pytest tests/system -m system` |
| CSV→Parquet converters (`scripts/csv_to_parquet_converter.py`, `legacy_src/convert_*`) | `pytest tests/utils/test_converter_*` |
| DataManager loading logic | `pytest tests/utils/test_data_manager.py`, integration tests |
| Strategy entry/exit logic | corresponding `tests/strategies/<strategy>/test_*` |
| Anytime new HTML/CSS assets are added | visual smoke test + `pytest tests/system/test_report_system.py::test_trade_report_contents -m system` |

**How to extend**:  When you add a new critical system test (e.g. for live-runner reporting), append a row to this table specifying the code areas that should trigger a re-run of that test. 