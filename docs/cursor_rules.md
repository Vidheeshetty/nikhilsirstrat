# Cursor Rules – Contribution Guidelines

This repository is used with the Cursor AI pair-programming agent.
The rules below keep the prompt tidy **and** make it easy to evolve.

1. Keep the file modular – each rule should be a single bullet so that tooling can update/append automatically.
2. If you change workflow scripts (`1dev_com.sh`, `2sync_main.sh`) also update this doc so humans & AI stay in sync.
3. Avoid recursive references: a rule must not instruct Cursor to rewrite *these* rules.
4. Do **not** leak secrets or tokens in examples.
5. Prefer explicit over implicit – spell out file paths, branch names.
6. Add new sections rather than editing history; deprecate with a strike-through comment.

## Strategy Development Framework Rules

### Before Creating a New Strategy:
1. **ALWAYS follow the standardized framework** - All strategies must conform to the [Strategy Development Framework](./development-standards/strategy-development-framework.md).
2. **Use the structure template** - Follow the exact directory structure defined in [Strategy Structure Template](./development-standards/strategy-structure-template.md).
3. **Extend BaseStrategy** - All strategies must inherit from `utils.strategy.base_strategy.BaseStrategy`.
4. **Implement required modules** - Create all required modules: `entry.py`, `exit.py`, `risk.py`, `position.py`.

### When Modifying Existing Strategies:
1. **Assess framework compliance** - Check current strategy against [Strategy Validation Checklist](./development-standards/strategy-validation-checklist.md).
2. **Plan incremental refactoring** - Bring strategies into framework compliance gradually.
3. **Identify utils integration opportunities** - Look for code that can be moved to utils package.
4. **Maintain backward compatibility** - Ensure modifications don't break existing functionality.
5. **Update documentation** - Reflect changes in strategy and framework documentation.

### Strategy Architecture Requirements:
1. **Modular design** - Split strategy logic into separate, focused modules as defined in [Module Implementation Guide](./development-standards/module-implementation-guide.md).
2. **Consistent naming** - Use PascalCase for strategy names, snake_case for files, follow established conventions.
3. **Proper exports** - Each module must define `__all__` with public interface.
4. **Type safety** - All functions must have proper type hints and docstrings.

### Utils Integration Priorities:
1. **Move common patterns to utils** - Identify repeated code across strategies that can be centralized.
2. **Use existing utils functions** - Leverage `utils.strategy.indicators`, `utils.strategy.risk`, etc.
3. **Propose new utils modules** - When creating reusable components, consider adding to utils.
4. **Maintain strategy independence** - Ensure strategies can still be customized without breaking utils integration.

### Runner Implementation:
1. **Both runners required** - Implement both single and batch runners following the established patterns.
2. **Use platform utilities** - Leverage `utils.runners.base_batch_runner.BatchRunner` for batch processing.
3. **Proper reporting** - Use `ReportController(mode="backtesting")` for generating reports.
4. **Integration compliance** - Ensure runners integrate properly with platform systems.

### Before Submitting Strategy Code:
1. **Complete validation checklist** - Go through the entire [Strategy Validation Checklist](./development-standards/strategy-validation-checklist.md).
2. **Test all imports** - Verify all modules can be imported without errors.
3. **Run validation commands** - Execute the test commands provided in the validation checklist.
4. **Check reference implementations** - Compare with `trend_riding` and `swing_range_expansion` strategies for consistency.

### Framework Compliance:
1. **No framework violations** - Do not create strategies that bypass the established framework.
2. **Utils integration** - Maximize reuse of platform utilities, avoid duplicate implementations.
3. **Consistent patterns** - Follow the same patterns established by reference strategies.
4. **Documentation requirements** - Ensure all modules have proper docstrings and type hints.

## Data Catalog Management Rules

### Before Converting CSV to Parquet:
1. **ALWAYS check `DATA_CATALOG.md` first** - This file contains the definitive inventory of all converted data with paths and timestamps.
2. **Verify if data already exists** - Check if the source CSV has already been converted by looking for matching paths in the catalog.
3. **Check source CSV timestamps** - Compare modification dates of source CSV files with catalog entries to determine if re-conversion is needed.
4. **Only convert if necessary** - Do not re-run conversion scripts if data already exists and is up-to-date.

### Data Catalog Documentation:
1. **Include source CSV path** - Each catalog entry must reference the original CSV file path for traceability.
2. **Include conversion timestamp** - Record when the conversion was performed, not when the catalog file was generated.
3. **Include CSV modification date** - Track the last modified date of the source CSV to detect changes.
4. **Use replace, not append** - Catalog entries should be updated/replaced, not duplicated when re-running conversions.

### Efficiency Rules:
1. **Check before create** - Always verify existing data availability before assuming conversion is needed.
2. **Validate data accessibility** - Test that existing catalog data can be loaded before declaring it "not ready".
3. **Document data status** - Clearly indicate whether data is ready, needs conversion, or has issues.
4. **Avoid redundant work** - If data exists and is accessible, focus on usage documentation rather than re-creation.

### Recommended Tools:
1. **Use smart_convert.py** - Always use `python scripts/smart_convert.py --config <config.yaml>` instead of direct converter calls.
2. **Check status first** - Run `python scripts/check_catalog_status.py --config <config.yaml>` to verify conversion necessity.
3. **Reference DATA_CATALOG.md** - Always check this file first to see what data is already available and when it was last updated.

## Repository Root Hygiene Rules

1. **Keep the root folder clean** – Only core repository artifacts should live at the root (e.g., `README.md`, `LICENSE`, top-level config files).  
2. **Do NOT add new feature docs, data notes, or strategy files directly under root.**  Think about the most appropriate sub-folder (`documentation/`, `docs/`, `examples/`, `config/`, etc.) and place the file there instead.  
3. **Ask first if unsure** – If the correct folder is unclear, discuss or reference existing documentation layout before committing a file to the root directory.  
4. **Migration responsibility** – When you encounter legacy files in the root that belong elsewhere, move them to the proper location and update links accordingly.  

## Static Type-Checking Rules (mypy)

1. All *core* modules under `src/` **must** pass `mypy` using the repository-level configuration (`mypy.ini`).  
   • The commit gate runs `mypy src --explicit-package-bases`; keep it clean.  
2. External/third-party libraries are allowed via `ignore_missing_imports=True`; when possible, add proper stubs (`types-PyYAML`, `pandas-stubs`, etc.) and remove the suppression.  
3. Error codes listed in `disable_error_code` inside `mypy.ini` provide a *temporary* shield while we add richer typing; contributors should aim to **remove** these codes over time.  
4. New or heavily-modified files should include meaningful type hints and avoid introducing new mypy errors—do **not** rely on the global suppressions.  
5. When adding new folders, update `mypy.ini` `exclude` pattern if they should be skipped, and ensure the path setup doesn't create duplicate module names.  