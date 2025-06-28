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
