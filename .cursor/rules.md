# 🚦 Cursor Coding Rules & Development Standards for NautilusTrader

## 1. Documentation & Versioning

* Always refer to the official NautilusTrader documentation located at: `nautilus_trader/docs/`
* Add headers to each file with version and reference:

  ```python
  # NautilusTrader Version: 1.86.0
  # Reference: nautilus_trader/docs/
  ```

## 2. Prompting & Templates

* Use structured prompts that mention:

  * Strategy name and logic type
  * Data type (TICK or BAR)
  * Instrument (futures, options, etc.)
  * Expected test behavior
* Refer to prompt templates in `.cursor/templates/`.
* Use predefined templates like `strategy_creation.md` and `test_case.md` to reduce inconsistency in format and naming.

## 3. Test-Driven Development (TDD)

* Write tests first when feasible (test-driven development).
* Comment expected behavior above code blocks, e.g.:

  ```python
  # Expected: Enter long after SMA cross-over
  ```
* Store tests using a structured hierarchy:

  ```
  /tests/
    /strategies/
      /trend_riding/
        test_entry.py, test_exit.py, ...
    /integration/
    /system/
    /selenium/               # Browser automation tests
  ```
* Do not replicate test scaffolding. Use shared logic and reuse where applicable.

### 3.1 Selenium Testing Framework (UI/Chart Testing)

**MANDATORY**: All UI development must use the established Selenium testing framework instead of manual browser testing.

#### 3.1.1 Test Categories & Markers

Use pytest markers to categorize tests by lifecycle:

```python
@pytest.mark.dev      # Development phase tests (temporary, detailed)
@pytest.mark.prod     # Production tests (permanent, core functionality)  
@pytest.mark.debug    # Debug and exploration tests
@pytest.mark.selenium # Browser automation tests
@pytest.mark.chart    # Chart functionality tests
@pytest.mark.realtime # Real-time data tests
@pytest.mark.performance # Performance benchmark tests
```

#### 3.1.2 TDD Workflow for UI Development

**Development Phase:**
1. Write detailed development tests with `@pytest.mark.dev`
2. Run: `./scripts/testing/run_selenium_tests.sh dev --headed`
3. Use tests to guide implementation and define "done" criteria
4. Add performance benchmarks: `./scripts/testing/run_selenium_tests.sh performance`

**Stabilization Phase:**
1. Convert essential tests to `@pytest.mark.prod` 
2. Remove/consolidate granular development tests
3. Run: `./scripts/testing/run_selenium_tests.sh prod --headless --parallel`
4. Add to CI/CD pipeline

#### 3.1.3 Page Object Model (POM)

**MANDATORY**: Use Page Object Model for all UI tests:

```python
# tests/selenium/page_objects/
dashboard_page.py    # Dashboard interactions
chart_page.py        # Chart-specific interactions
```

#### 3.1.4 Test Execution Commands

```bash
# Quick validation
python3 scripts/testing/validate_selenium_framework.py

# Development testing (headed, verbose)
./scripts/testing/run_selenium_tests.sh dev --headed --verbose

# Production testing (headless, parallel)  
./scripts/testing/run_selenium_tests.sh prod --headless --parallel

# Performance benchmarking
./scripts/testing/run_selenium_tests.sh performance

# Debug mode with state capture
./scripts/testing/run_selenium_tests.sh debug --headed
```

#### 3.1.5 Performance Benchmarks

All UI tests must meet these performance criteria:
- Chart load time: < 5 seconds
- Dashboard load time: < 10 seconds  
- Memory usage: < 100MB
- Chart interactions: < 1 second response
- Real-time updates: < 30 seconds detection

#### 3.1.6 Test Lifecycle Management

**Key Principle**: Tests serve as development tools during active work, then consolidate to essential tests for long-term maintenance to avoid test suite bloat.

**Lifecycle:**
1. **Add granular dev tests** during feature development
2. **Use tests to guide implementation** and define "done" criteria  
3. **Remove/consolidate tests** once features stabilize
4. **Keep essential tests** for regression protection

#### 3.1.7 Dependencies

Install Selenium testing dependencies:
```bash
pip install -r requirements-selenium-testing.txt
```

#### 3.1.8 Cursor UI Development Mandate

**NEVER** ask users to manually test UI changes in browser. Always:
1. Write Selenium tests first (TDD approach)
2. Use tests to validate functionality
3. Run automated test suite to verify changes
4. Only ask for manual verification if automated tests are insufficient

**Framework Location**: `tests/selenium/` with complete Page Object Model implementation

## 4. Code Reuse with Utils

* Place shared logic inside `/utils/` to avoid duplication:

  ```
  /utils/
    /data_adapters/        # Data import/export converters
    /strategy/             # Indicators, SL/TP, base strategy
    /runners/              # Common backtest/live runners
    /execution/            # Order/position helpers
    /validators/           # Schema, price, and symbol checks
  ```
* Strategy-specific code should remain inside each strategy package.

## 5. Modular Strategy Structure

* Split strategy logic into logical components for clarity:

  ```
  /src/
    /strategies/
      /trend_riding/
        entry.py
        exit.py
        position.py
        risk.py
        config.py
        strategy.py
        /runner/
          /backtest_runner/
            engine.py
            metrics.py
            hooks.py
            config.py
          paper_runner.py
          live_runner.py
  ```

## 6. Code Style & Conventions

* Inline comments must stay on the same line where possible:

  ```python
  price = self.mid_price()  # fetch current mid price
  ```
* Avoid unnecessary line breaks. Be concise.
* Use type hints and follow PEP8 formatting.
* All public functions should include docstrings:

  ```python
  def calculate_signal(price: float) -> bool:
      """
      Returns True if signal condition is met.
      """
  ```

### 6.1 Ruff Linting Standard

* **Ruff** is the canonical linter / formatter for this repository.
* All new or modified Python files **must** pass the project's linting standards before they are committed.

#### 6.1.1 Core Development Paths (Strict)
For files in core development paths, **zero errors** are allowed:
```bash
# These paths must pass ruff check with no errors:
src/ utils/ tests/ scripts/run_backtest.py scripts/run_batch_backtest.py scripts/data_import/
```

#### 6.1.2 Legacy/Debug Paths (Relaxed)
For legacy and debug code, unused imports (F401) are ignored but other errors must be fixed:
```bash
# These paths use relaxed rules:
legacy_src/ old-code/ debug-code/ legacy_tests/
```

#### 6.1.3 Cursor Auto-Linting Workflow

**MANDATORY**: After every Cursor edit to Python files, automatically run:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Auto-format the edited files
ruff format <edited_files>

# 3. Fix auto-fixable issues
ruff check <edited_files> --fix

# 4. Check for remaining errors
ruff check <edited_files>
```

**If any errors remain after step 4**: 
- Fix them immediately or ask user for guidance
- **Never** leave unfixed linting errors in core development paths
- For legacy paths, only fix critical errors (E722, F823, syntax errors)

#### 6.1.4 Specific Error Handling

**Critical errors that must always be fixed:**
- **E722**: Bare `except:` clauses → Change to `except Exception:`
- **F823**: Variable referenced before assignment → Fix import order
- **F841**: Unused variables → Remove or prefix with `_`
- **Syntax errors**: Always fix immediately

**Acceptable to ignore in legacy code only:**
- **F401**: Unused imports (legacy debugging code)
- **E402**: Module imports not at top (legacy path manipulation)

#### 6.1.5 Development Script Alignment

The helper script `1dev_com.sh` runs:
```bash
ruff check --extend-ignore F401 "${CORE_PATHS[@]}"
```

This aligns with the core development standard (strict) while allowing F401 for debugging imports.

#### 6.1.6 Pre-Commit Checklist for Cursor

Before any commit, Cursor must verify:
- [ ] All edited Python files pass `ruff format --check`
- [ ] All edited core path files pass `ruff check` (zero errors)
- [ ] All edited legacy files pass `ruff check --extend-ignore F401,E402`
- [ ] No bare `except:` clauses remain anywhere
- [ ] No undefined variable references (F823) remain

## 7. Reporting & HTML Output

### 7.1 Centralized CSS Styling

* All HTML reports must link to a shared stylesheet at:

  ```
  /assets/css/report-style.css
  ```
* Do not embed inline CSS or style locally in the output HTML.

### 7.2 HTML Template Reuse

* Store reusable templates (e.g., Jinja2) at:

  ```
  /utils/templates/
  ```

### 7.3 Cursor Prompting for Reports

* When prompting Cursor to generate reports or dashboards, specify:

  * Use `/assets/css/report-style.css`
  * Reference shared HTML base templates if applicable

## 8. User Documentation System

### 8.1 Folder Structure and Format

* All user-facing documentation must be placed inside:

  ```
  /UserDocumentation/
  ```
* Use **HTML format** for each topic or module (not Markdown).
* Each HTML file must:

  * Use `/assets/css/report-style.css` for consistent styling.
  * Be modular (1 topic per file).
  * Be linked from the main index.html.

### 8.2 Main Index Page

* The file `/UserDocumentation/index.html` must:

  * Serve as the homepage for all documentation.
  * Contain a navigation menu with links to all topic pages.
  * Be updated automatically or manually whenever a new topic doc is added.

### 8.3 Cursor Prompting for Docs

When using Cursor to generate user docs, specify:

* The purpose of the doc (e.g. "How to run the trend riding backtest runner").
* That the output should be in **HTML**.
* That the style should link to:

  ```html
  <link rel="stylesheet" href="/assets/css/report-style.css">
  ```
* That it should follow the layout standards defined in `base_report.html` if templates are in use.

**Prompt example:**

> "Generate a user-facing HTML guide for using the `nser_bar_to_parquet.py` converter. It should describe required columns, output structure, expected file locations, and link back to index.html."

### 8.4 Suggested Subtopics (HTML Files)

Each of these should be their own HTML file under `/UserDocumentation/`:

```
/UserDocumentation/
  index.html
  strategy_trend_riding.html
  how_to_backtest.html
  paper_trading_setup.html
  data_conversion_tools.html
  config_parameters.html
```

### 8.5 Documentation Triggers in TDD Workflow

* Once all tests for a module/function/strategy pass:

  * A corresponding HTML doc must be written or updated.
  * This should be treated as part of the 'definition of done.'

### 8.6 Style & Accessibility

* Use semantic HTML tags (`<section>`, `<header>`, `<article>`, etc.).
* Ensure all pages are mobile-friendly and screen-reader accessible.
* Avoid inline styles — use only `/assets/css/report-style.css`.

## 9. System-Level Tests (Heavy)

* Tests marked with `@pytest.mark.system` live under `tests/system/` and exercise complete data → runner → reporting pipelines.
* They are **excluded from the default `pytest` run** via the marker rules in `.pytest.ini` and must be executed manually when a change can affect them.
* Cursor edits that touch any of these areas MUST run – and pass – the relevant system tests **before commit**:
  * Reporting / renderer modules under `utils/reporting/`
  * Engine / Runner orchestration that populates trade dictionaries
  * Data-conversion utilities that feed end-to-end back-tests

### 9.1 Required Command for the Reporting Module

When modifying or enhancing the reporting subsystem you **must** run:

```bash
pytest tests/system/test_report_system.py::test_trade_report_contents -m system
```

If new system tests are added for other modules, update this section with the exact command string to run them.

### 9.2 Test-Impact Matrix

For maintainability the full **Test-Impact Matrix** now lives in
`docs/test_impact_matrix.md`.  Update that file whenever you add a new system
or unit test which should be re-run after certain code areas change.

### 9.3 **Automation Hint for Cursor / CI**

*If any edit touches paths matching the glob patterns below, Cursor (or the CI
helper script) **MUST automatically run _only_ the heavy system test
`tests/system/test_report_system.py::test_trade_report_contents` with the
`-m system` marker, and fail fast if that test fails.*

```
utils/reporting/**
utils/reporting/**/*.py
utils/reporting/renderers/**
```

*Rationale*: these locations directly influence the HTML/CSV report
structures validated by the system test.  Running the full unit-suite alone
is insufficient to catch template or rounding regressions.

## 10. Virtual-Environment Mandate

* **All Python commands (scripts, `pytest`, linters, etc.) must be run inside the project's virtual environment.**
* The standard location is `. /venv/` created via `python -m venv venv && source venv/bin/activate`.
* Cursor tool calls that invoke the shell **must start with `source venv/bin/activate`** (if not already active) before running any Python command.
* System tests that rely on compiled or optional packages (e.g. `nautilus-trader`) should assert the import works and skip gracefully if not available:
  ```python
  pytest.importorskip('nautilus_trader')
  ```
* CI workflows must likewise activate the venv or use `pipx run` to ensure consistent dependency resolution.

> **Rule**: PRs or Cursor edits that create/rename significant tests **must** update `docs/test_impact_matrix.md` in the same commit.  CI should fail if the matrix is stale.

## 11. Pluggable Strategy Architecture

**MANDATORY: All new strategies MUST use the pluggable architecture pattern established in SMA Fractal Scalper V2.**

### 11.1 Architecture Components

#### 11.1.1 Indicators Layer (`utils/indicators/`)
- Pure mathematical calculations (SMA, EMA, RSI, Fractal, etc.)
- Configuration-driven management via YAML
- Chart visualization integration
- Reusable across strategies

#### 11.1.2 Signal Generation Layer (`utils/signals/`)
- Combines indicator outputs using configurable logic
- Pluggable signal strategies (SMA crossover, RSI+Bollinger, etc.)
- Confidence scoring and filtering
- Separate from strategy execution

#### 11.1.3 Strategy Execution Layer (`src/strategies/*/`)
- Focuses on position management and risk control
- Uses indicator and signal managers
- Configuration-driven indicator/signal selection

### 11.2 Implementation Requirements

- **Indicators**: Inherit from `BaseIndicator`, implement in `utils/indicators/implementations.py`
- **Signals**: Inherit from `BaseSignalGenerator`, implement in `utils/signals/implementations.py`
- **Configuration**: Separate YAML files for indicators (`indicators.yaml`) and signals (`signals.yaml`)
- **Testing**: Individual component tests + integration tests
- **Documentation**: Signal generation logic documented in strategy folder README.md

### 11.3 Benefits

- ✅ Easy testing of individual components
- ✅ Dynamic enable/disable of indicators/signals
- ✅ Chart visualization configuration
- ✅ Reusable components across strategies
- ✅ Configuration-driven development

### 11.4 Required Strategy Structure

```
src/strategies/my_strategy/
├── __init__.py
├── config.py           # Strategy configuration
├── strategy.py         # Main strategy class
├── indicators.yaml     # Indicator configuration
├── signals.yaml        # Signal generation configuration
└── README.md          # Signal logic documentation
```

### 11.5 Example Reference Implementation

See `src/strategies/sma_fractal_scalper_v2/` for complete reference implementation.

### 11.6 Mandatory Strategy Test Suite

For **every new strategy** created with the template in Section 11.4, you **must** add a matching test folder:

```
/tests/strategies/{strategy_name}/
├── test_strategy.py   # Core entry/exit & lifecycle logic
├── test_config.py     # YAML/Config loading & schema validation
└── test_runner.py     # Runner initialisation & paper-trading execution
```

* All tests use **pytest** and follow the existing marker convention (`@pytest.mark.dev`, `@pytest.mark.prod`, etc.).
* Broker / market-data dependencies must be **mocked** (e.g. `pytest-mock`, monkey-patching `utils.brokers.*`) so tests run offline & deterministically.
* `test_strategy.py` should cover:
  * entry/exit signal generation with sample bar data
  * position lifecycle (open → adjust → close)
  * edge-cases (no data, stale data, error handling)
* `test_config.py` validates:
  * YAML schema via `utils.validators.data_schema`
  * correct parsing into the strategy's `config.py` dataclass
* `test_runner.py` ensures the **paper-trading runner** starts, processes a mocked data stream, and reports trades without exceptions.
* **CI Enforcement**: a PR adding `src/strategies/{strategy_name}/` must fail if the corresponding test directory does not exist or `pytest -m prod` fails.
* Cursor must auto-generate skeleton test files when scaffolding a new strategy package.

## 12. Learning Documentation System

**MANDATORY: All significant learnings, fixes, and solutions MUST be documented in the learning log.**

### 12.1 Learning Log Location

* **Primary learning log**: `cursorrules.support/learning_log.md`
* **Format**: Tabular format with Date, Area, Lesson, Importance columns
* **Character limit**: ≤ 120 characters per lesson to maintain readability

### 12.2 What Must Be Documented

**CRITICAL (Importance: Critical)**:
- Complete system failures and their fixes
- Security vulnerabilities and patches
- Data corruption/loss prevention fixes
- Performance bottlenecks and optimizations

**HIGH (Importance: High)**:
- Configuration issues causing service failures
- Integration problems between components
- Testing framework improvements
- Architectural decisions with long-term impact

**MEDIUM (Importance: Med)**:
- Code quality improvements
- Refactoring lessons
- Development workflow optimizations
- Library/dependency learnings

### 12.3 Cursor Learning Documentation Workflow

**MANDATORY PRE-DEVELOPMENT**: Before starting any significant development work, Cursor MUST:

1. **Consult the learning log** (`cursorrules.support/learning_log.md`) for relevant past learnings
2. **Search memory** for related issues and solutions
3. **Reference applicable learnings** in the development approach
4. **Avoid repeating documented mistakes** by following established solutions

**MANDATORY POST-DEVELOPMENT**: After resolving any significant issue, Cursor MUST:

1. **Immediately update the learning log** with the fix
2. **Update memory** with the learning for future reference
3. **Escalate importance** if the same issue recurs (Med → High → Critical)
4. **Reference the learning** in future similar situations

**Examples of Pre-Development Consultation**:
- Before implementing web dashboard features → Check for UI/JavaScript module learnings
- Before adding new strategy components → Review strategy architecture learnings
- Before modifying configuration systems → Check configuration-related learnings
- Before implementing testing → Review testing framework learnings

### 12.4 Learning Log Entry Format

```markdown
| YYYY-MM-DD | Area | Lesson (≤120 chars) | Importance |
```

**Example**:
```markdown
| 2025-07-03 | Web Dashboard | Chart "Failed to initialize dashboard": (1) FastAPI needs `mimetypes.add_type('application/javascript', '.js')` before mounting static files for ES6 modules (2) ChartManager constructor accessed undefined `this.container.clientWidth` - use defaults, set in initChart(). Always use Selenium tests not manual testing. | Critical |
```

### 12.5 Automation and Enforcement

* The `1dev_com.sh` script parses **High** and **Critical** items and warns if patterns re-appear
* Cursor MUST check the learning log before implementing solutions to avoid repeating mistakes
* Each learning entry should be referenced when similar issues arise

### 12.6 Memory Integration

* All learning log entries MUST be stored in Cursor's memory system
* Memory entries should reference the learning log for detailed context
* Contradictory learnings should update/delete previous memories

## 13. Branch Workflow – dev ↔ main

* All day-to-day feature work should be committed to the **`development`** branch.
* After all tests pass **Cursor should ask**: *"Do you want me to commit & push these changes to development? Suggested message: <auto-generated message> (you can edit)."*  
  * If you reply **yes** (or `yes: <custom message>`), Cursor will run `./1dev_com.sh "<final message>"` in non-interactive mode so the commit goes straight to `development`.
  * If you reply **no**, nothing is committed and you keep full control.
* Use the helper script `1dev_com.sh` – it now supports a non-interactive flag `--msg "<commit message>"` which skips the prompt.
* At least once per day (or when work is stable) Cursor will similarly **prompt** whether to run `2sync_main.sh --yes` to fast-forward **`main`**.
* The `2sync_main.sh` script accepts `--yes` (skip prompt) and optional `--msg "<tag annotation>"` to run fully unattended.
* The script automatically:
  1. Ensures `pytest -q` passes.
  2. Runs the system report test (`pytest -m system tests/system/test_report_system.py::test_trade_report_contents`).
  3. Tags the merge commit with `ci:sync-main-YYYYMMDD`.
  4. Pushes `main` to origin.
* Cursor edits that touch either helper script **must** update this section and `docs/runbook.md` accordingly.

## 14. Paper Trading UI & User Management Architecture Rules

The following rules strengthen the front-end architecture, ensure consistency with the pluggable strategy pattern (Section 11) and align data contracts with the shared utils modules.

### 14.1 User & Strategy Session Architecture Rule
* Every dashboard/WebSocket session is defined by a tuple **(user_id, strategy_id)**.
* The **JWT access-token** (passed via `Authorization: Bearer <token>`) MUST include these claims:
  * `sub` → user id
  * `strategy` → active strategy key (e.g. `sma_fractal_scalper`)
  * `role` → UI role (`viewer`, `trader`, `admin`)
* FastAPI dependencies must resolve the token once and inject a `SessionContext` object so downstream routes / websocket handlers access `ctx.user_id` and `ctx.strategy` without re-parsing.
* Session state (last timeframe, hidden indicators, UI prefs) is cached in **Redis** (or an in-memory fallback) under the composite key `session:{user_id}:{strategy}`.

### 14.2 Modular UI Architecture Rule
* **MANDATORY**: All front-end logic lives as ES-modules under `web_dashboard/static/js/modules/`.
* Keep modules atomic: one class per feature (`ChartManager`, `IndicatorManager`, `StrategyPanel`, etc.).
* Shared helpers belong to `web_dashboard/static/js/utils/` and **must not** duplicate code already present in `utils/*` on the Python side.
* When adding a module export **both** a default class and named exports for helper functions to facilitate tree-shaking.
* Selenium Page-Objects must map one-to-one with major modules (e.g. `StrategyPanel` ↔ `strategy_panel.py`).

### 14.3 Paper Trading Dashboard Rule
* Route `/chart` is the single SPA entry-point.  Strategy selection happens via query-param `?strategy=<key>` or user preference.
* The dashboard **MUST** support multiple strategies in parallel (tabbed UI).  Opening a new tab with `?strategy=xyz` creates a new WebSocket channel without reloading the page.
* Dashboard state for each strategy is namespaced (store keys prefixed with `strategy.<key>.`).

### 14.4 TradingView Chart Integration Rule
* Use **Lightweight-Charts v5+** production bundle (`static/libs/lightweight-charts.standalone.production.js`).
* `ChartManager` must stay library-agnostic; it exposes generic methods (`addIndicator`, `addMarkers`, `fitContent`).
* Indicator visualisation happens exclusively through `IndicatorManager`; strategy-specific logic **must never** touch `ChartManager` internals.
* No direct DOM mutation for drawing – always go through the Lightweight-Charts API.

### 14.5 Strategy Detail Panel Rule
* The right-hand **Strategy Panel** shows live metrics (status, position, last signal, P&L, win-rate, etc.).
* Backend emits `strategy_update` events over WebSocket; the panel subscribes via `DataService` and re-renders diff-patch style.
* Selenium tests (`TestChartIndicators.test_trading_signals_on_chart`) must assert the panel updates when a `strategy_update` arrives.

### 14.6 Data API Route Convention Rule
| Purpose | HTTP Prefix | WS Prefix | Example |
|---------|-------------|-----------|---------|
| Chart data & indicators | `/api/chart/*` | `/ws/chart` | `/api/chart/indicators?strategy=sma` |
| Strategy ops / state    | `/api/strategy/*` | `/ws/strategy` | `/api/strategy/toggle?sma` |
| User auth & prefs       | `/api/user/*` | n/a | `/api/user/preferences` |
* All new routes **must** follow this convention; mixed naming (`/api/chart_data`) is forbidden.

### 14.7 FastAPI User Auth Rule
* Implement **OAuth2 Password + JWT** (`fastapi.security.OAuth2PasswordBearer`).
* Anonymous requests return **401**; front-end redirects to `/login`.
* Never trust headers like `X-User-Id` alone – always validate the JWT.
* Utilities for token generation / verification live in `utils/auth/` and are unit-tested.

### 14.8 Live Mode Ready Rule
* Features built for paper/backtest **must** degrade gracefully and remain compatible with **live-trading** mode.
* **No HTTP polling**: all real-time UI updates flow via WebSocket events (`bar_update`, `indicator_update`, `strategy_update`).
* Provide fallback UI stubs when live data is unavailable (e.g. greyed-out trend status).
* Selenium real-time tests (`@pytest.mark.realtime`) must pass with the `--live-mode` flag, verifying charts and panels update against a live data feed.

> **Enforcement**: Cursor must refuse a commit or raise a warning if new UI/API code violates any rule in Section 14.

## 15. Strategy Parameter Versioning & Experiment-Tracking Rules

These rules formalise how parameters, sweeps, and experiment metadata are stored and tested.  They complement Section 11 (pluggable strategies) and Section 12 (learning log).

### 15.1 PostgreSQL Parameter Versioning
* Each strategy **must** persist its configuration parameters in the `strategy_parameters` table:
  | Column | Type | Notes |
  |--------|------|-------|
  | id | SERIAL PK |  |
  | strategy_key | TEXT | `sma_fractal_scalper_v2` |
  | version | INT  | auto-increment per strategy |
  | yaml | JSONB | canonical YAML parsed to JSONB |
  | created_at | TIMESTAMPTZ | default `NOW()` |
* The dataclass in `config.py` needs a `__version__` attribute that is synchronised with the DB row.
* Runner initialisation logs **both** the hash of the YAML blob and the DB `version` id.  Mismatch = hard error.

### 15.2 Parameter-Sweep Tracking (Grid & Monte-Carlo)
* Sweeps are recorded in `parameter_sweeps` with:
  | sweep_id | strategy_key | method (`grid`/`mc`) | hyperparams JSONB | created_by |
* Each run generated by a sweep inserts into `parameter_runs` referencing `sweep_id` + `param_set_hash`.
* `utils.experiments.sweeper` must populate these tables automatically.
* Sweep status (`queued`, `running`, `done`, `failed`) is updated via `utils.runners.base_batch_runner` hooks.

### 15.3 Run Metadata vs Results Separation
* Store immutable *metadata* in `run_metadata` keyed by `(user_id, strategy_key, param_version, run_id)`; include timestamps, git commit hash, Docker image tag.
* Store heavy *results* (trades, metrics) in `run_results` referencing the same PK; large JSONB blobs or S3 link are acceptable.
* Reporters (`ReportController`, `PaperTradingReporter`) fetch from **run_results**, not from metadata.

### 15.4 Mandatory Runner Tests with Mocked Feeds
* Each runner (`backtest_runner`, `papertrade_runner`, `live_runner`) **must** have tests:
  * Path: `tests/runners/test_{runner_name}.py` or inside strategy-specific folder.
  * Use `pytest-mock` or fixtures to monkey-patch broker feeds (no live data).
  * Assert:
    * runner initialises with given `param_version`
    * inserts correct metadata rows
    * produces at least one trade in the mocked scenario
* Missing tests → CI fails; Cursor must refuse commit.

> **Enforcement**: CI migration scripts create/maintain the four tables above; PRs touching runners/config must run integration tests against a **`postgres:14-alpine`** service in Docker-Compose CI.
