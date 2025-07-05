# Cursor Rules – Contribution Guidelines

(THIS FILE MOVED from `docs/cursor_rules.md` on 2025-06-30 to consolidate Cursor-specific guidance.)

_All section headings and content are unchanged; only the path moved._

For the learning log see `cursorrules.support/learning_log.md`.

---

// ... existing content from previous rules file ... 

## 18 – Development Pipeline (Dev Stack)
1. The CI workflow **deploy-dev.yml** builds the `development` branch and deploys it to **https://dev.synaptictrading.com**. This environment is called the *Development stack*.
2. A separate *Staging* environment will be introduced later. When that happens, update this rules file and `docs/deployment/CI_CD_PIPELINES.md` accordingly.
3. Any change to GitHub workflows, deployment scripts, or server configuration **MUST** be mirrored in `docs/deployment/CI_CD_PIPELINES.md` in the same commit to avoid drift.
4. All pipelines (development, staging when available, production) must stay green; failing pipelines block merges to `main`. 