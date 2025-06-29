# Cursor Rules – Contribution Guidelines

This repository is used with the Cursor AI pair-programming agent.
The rules below keep the prompt tidy **and** make it easy to evolve.

1. Keep the file modular – each rule should be a single bullet so that tooling can update/append automatically.
2. If you change workflow scripts (`1dev_com.sh`, `2sync_main.sh`) also update this doc so humans & AI stay in sync.
3. Avoid recursive references: a rule must not instruct Cursor to rewrite *these* rules.
4. Do **not** leak secrets or tokens in examples.
5. Prefer explicit over implicit – spell out file paths, branch names.
6. Add new sections rather than editing history; deprecate with a strike-through comment. 