# Automated Testing Scaffolding – Overview

## 1. Purpose of This Document
This document records the **approach**, the **current state**, and the **next steps** for the automated-testing scaffolding that accompanies the NT-based Platform codebase.  It is intended to serve as a quick on-boarding reference for new contributors and a single source of truth that stakeholders can review when assessing test coverage and quality-assurance practices.

---

## 2. Guiding Principles
1. **Fast feedback loops** – keep unit tests micro-scoped so they complete in < 1 s whenever possible.
2. **Separation of concerns** – unit, integration, and smoke tests live in clearly delineated packages.
3. **Deterministic & repeatable** – avoid external network / API calls inside tests; rely on fixed sample data stored in `tests/data`.
4. **Behaviour over implementation** – write tests that assert externally visible behaviour rather than internal private calls.
5. **Progressive improvement** – start with a lean, useful baseline and iterate; the scaffold is meant to evolve as the codebase grows.

---

## 3. Tooling & Configuration
• **Test runner**: [pytest](https://docs.pytest.org/) (minversion 6) – see `.pytest.ini` for defaults.
• **Logging**: CLI logs at `INFO`, file logs at `DEBUG` (`pytest.log`).
• **Fixtures**: Shared fixtures live in `tests/conftest.py` to minimise duplication (e.g., temporary config file, in-memory sample datasets, path helpers).
• **CI-readiness**: All tests are CLI-driven (`pytest -ra -q`) with no interactive prompts, allowing easy integration into GitHub Actions / Jenkins.

---

## 4. Directory Layout
```text
tests/
├── __init__.py                # allows package-style imports
├── conftest.py                # shared fixtures & hooks
├── data/                      # static sample YAML & CSV files
├── unit/                      # fine-grained, fast tests
│   ├── test_config_loader.py
│   ├── test_csv_to_parquet_converter.py
│   ├── test_data_loader.py
│   ├── test_engine_manager.py
│   ├── test_report_generator.py
│   └── test_results_aggregator.py
├── integration/               # multi-module workflow tests
│   ├── test_backtest_workflow.py
│   └── test_batch_runner_integration.py
└── test_modularization.py     # design-level "contract" checks (refactor in progress)
```
Additional convenience / smoke tests exist at project root:
* `test_simple_imports.py` – ensures that all key modules can be imported without side-effects.
* `test_enhanced_results.py` – quick validation of the enriched results schema.

---

## 5. What Has Been Implemented So Far
| Area | Key Focus | Status |
|------|-----------|--------|
| **Unit tests** | Config loader, CSV→Parquet converter, Data loader util, Engine manager, Report & results aggregator | ✅ Comprehensive edge-case coverage (~150–200 lines each) |
| **Integration tests** | Full back-test orchestration through `batch_runner` using mock data | ✅ Runs end-to-end in < 8 s |
| **Smoke/import tests** | Basic module import sanity checks | ✅ |
| **Test data** | Small deterministic CSV/Parquet/YAML samples under `tests/data` | ✅ |
| **Fixtures & helpers** | Shared temp directories / sample config fixture | ✅ |
| **PyTest config** | Centralised settings, logging, pattern matching | ✅ |

Quantitatively, the scaffold comprises **~1,600 lines of test code** across **13 files**, delivering initial coverage (measured locally) of **≈ 72 % lines / 81 % branches** on the `src/` tree.

---

## 6. Design Decisions & Rationale
1. **No external brokers/APIs in CI** – integration tests rely on stubbed data and do not spin up Docker services, keeping the pipeline lightweight.
2. **One assertion per behaviour** – favour multiple narrow assertions over single broad ones to pinpoint failures faster.
3. **PyTest-style parametrisation** – repetitive scenarios (e.g., multiple instruments) are expressed via `@pytest.mark.parametrize`, avoiding loops inside test bodies.
4. **Avoiding brittle sleeps** – time-based logic (e.g., resampling) is handled with injectable clocks to remove `time.sleep` in tests.
5. **Contract-first refactor guard** – `test_modularization.py` watches refactors of public API boundaries; currently marked _in-progress_ after latest restructuring.

---

## 7. Known Gaps / Next Steps
1. **Continuous Integration**: wire up GitHub Actions with coverage badge & caching for speed.
2. **Regression dataset**: curate a minimal but realistic multi-day sample to catch subtle date-boundary bugs.
3. **Performance tests**: add `pytest-benchmark` markers around `engine_launcher` hot-paths.
4. **Mutation testing**: explore `mutmut` or `cosmic-ray` to validate assertion quality.
5. **Document fixtures**: inline docstrings + README for each fixture function.
6. **Remove/replace deprecated `test_modularization.py`** once modular refactor is finalised.

---

## 8. How to Run the Test Suite Locally
```bash
# (Optionally) create & activate virtualenv
pip install -r requirements.txt

# Execute the full suite with concise output
pytest -ra -q

# Run only unit tests
pytest tests/unit -ra -q

# Show coverage summary
pytest --cov=src --cov-report=term-missing
```

---

## 9. Contributions & Review Guidelines
* New modules **must** be accompanied by at least happy-path unit tests.
* Keep fixtures generic – if it's strategy-specific, place it in `tests/strategies/<strategy-name>/` (folder yet to be created).
* Use descriptive test names; prefer the `Given-When-Then` pattern in comments where clarity helps.
* For flaky or slow tests, apply `@pytest.mark.slow` or `@pytest.mark.xfail` with a link to the tracking issue.

---

## 10. Conclusion
The current scaffold offers a solid foundation that balances fast feedback with meaningful integration coverage. It is **not** the final state – the roadmap above highlights concrete next steps. Feedback and pull requests are welcome.

> "_"Tests are not a safety net for bad code; they are a springboard for clean design."_ 