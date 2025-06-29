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
  ```
* Do not replicate test scaffolding. Use shared logic and reuse where applicable.

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
* All new or modified Python files **must** pass `ruff check --fix` with **zero errors** before they are committed.
* Recommended command sequence for Cursor edits:

  ```bash
  ruff format .                 # auto-format (PEP-8 compliant)
  ruff check . --fix            # apply safe fixes, then rerun to ensure clean
  pytest -q                     # always follow with tests
  ```

* The helper script `1dev_com.sh` runs `ruff check .` by default.  If it fails, the commit is aborted; fix or stage the Ruff auto-fixes and rerun.
* When introducing third-party code snippets, adjust import order / remove unused imports so Ruff (rules **E**, **F**, **I**) stays green.  Disable a rule only with a *local* `# noqa: <rule>` comment and include a justification.

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

## 11. Branch Workflow – dev ↔ main

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
