# Continuous Integration & Continuous Deployment (CI/CD)

> **Document owner:** DevOps team.  
> Keep this file in sync with GitHub Actions workflows and deployment scripts.

---

## 1. Branch Strategy & Environments

| Branch / Tag | Environment | URL | Workflow |
|--------------|-------------|-----|----------|
| `development` | **Development stack** | https://dev.synaptictrading.com | `.github/workflows/deploy-dev.yml` |
| `main`        | — (no auto-deploy) | — | manual merge source |
| Git tag `vX.Y.Z` | **Production** | https://synaptictrading.com | `.github/workflows/docker-deploy.yml` |
| *future* `staging` branch | **Staging stack** (TBD) | e.g. https://staging.synaptictrading.com | to be defined |

---

## 2. Workflows

### 2.1 Development pipeline – `deploy-dev.yml`

* Trigger: `push` to `development` (plus manual `workflow_dispatch`).
* Steps:
  1. Checkout & install Python deps
  2. Run unit/integration tests + Selenium UI smoke tests
  3. Build Docker image `docker.io/<DOCKER_USERNAME>/ntplatform:dev-<sha>`
  4. Push image to Docker Hub
  5. SSH to server and run `scripts/v2/deploy/launch_v2.sh dev` (deploy to Development stack)
  6. Discord notification
* Required secrets: `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY`

### 2.2 Production pipeline – `docker-deploy.yml`

* Trigger: manual (`workflow_dispatch`)
* Input: `version` (e.g. 1.3.0) & `environment` (production/staging once available)
* Steps: validate tag, build & push image(s), deploy via SSH, health-check, cleanup, summary.

---

## 3. Secrets

| Secret | Purpose |
|--------|---------|
| `DOCKER_USERNAME` / `DOCKER_PASSWORD` | Docker Hub push/pull |
| `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY` | SSH deploy |
| `DISCORD_WEBHOOK` | Optional notification |

---

## 4. Adding a Staging Environment (future)

When a dedicated staging environment is introduced:
1. Create a new branch (e.g. `staging`) or use GitHub Environments.
2. Add a new workflow (or extend existing) that deploys to `staging.synaptictrading.com` using a compose `--profile staging`.
3. Update this document **and** `cursorrules.support/rules.md` Section 18.

---

## 5. Rollback Procedure

1. Identify a previous tag (e.g. `v1.2.5`).
2. Trigger `docker-deploy.yml` with that version.
3. Verify health endpoint `/api/status`.

---

## 6. Change Log

* **2025-07-05** – Initial version (Development + Production).  
* **2025-07-05** – Terminology aligned: Development stack now; Staging reserved for future. 