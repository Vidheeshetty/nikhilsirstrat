# Docker Development Workflows – Option 2 vs Option 3

This note expands on the two "development-inside-Docker" patterns we discussed.
It is **not** a prescription – pick whichever matches your team's cadence and
CI/CD layout.

---
## 0. Terminology Quick-Start

| Term                | What it means in this repo                                              |
|---------------------|---------------------------------------------------------------------------|
| *App Container*     | Image that would run in production (paper-trading engine, back-tests).    |
| *Dev Container*     | A throw-away container started **from the same image** but with the       |
|                     | source tree bind-mounted and `bash` (or `zsh`) as its *entry point*.      |
| *Bind Mount*        | `-v $(pwd):/workspace` – host files instantly visible inside container.  |
| *Hot Reload*        | Code changes propagate without a rebuild because of bind-mount.          |

---
## 1. Option 2 – "Dev Container"

### 1.1 Compose Snippet
```yaml
services:
  devshell:
    build: .                # Re-uses the regular Dockerfile
    command: bash           # 👈 launches an interactive shell
    volumes:
      - .:/workspace        # Bind-mount checkout → /workspace in container
    env_file: .env          # (optional) export API keys etc.
    ports:
      - "8888:8888"        # Jupyter
      - "2345:2345"        # Delve / debugpy
```

### 1.2 How to Use
1. `docker compose up -d devshell`
2. In **Cursor**: Command Palette → *Attach to Container…* → `devshell`
3. All integrated terminals + tool calls now run **inside** the container.
4. Edit code as usual – files are synced instantly via the bind-mount.
5. When done: `exit` inside container or `docker compose down devshell`.

### 1.3 Pros / Cons
| Pros | Cons |
|------|------|
| Perfect parity with production libraries & OS libs | First-time build takes a few minutes |
| Zero rebuild when you only touch Python files | Need to expose ports for web UIs |
| Same workflow for Mac / Linux / Windows developers | IDE features that rely on host binaries (e.g. pyenv) are inside container instead |

### 1.4 FAQ
*"Drops you into bash instead of running the app"* means the container **starts a
shell prompt** (`bash`) as PID 1, so you can run tests, launch the strategy, or
install extra tools interactively, instead of immediately executing
`python run_paper_trading.py` (the usual CMD in the prod container).

---
## 2. Option 3 – "Live-Rebuild Image"

### 2.1 Idea
Keep your source code bind-mounted **but** rebuild the image whenever the base
system dependencies change (apt packages, Poetry libraries, etc.).

```
# dev-build.sh
DOCKER_BUILDKIT=1 docker build -t ntplatform:dev --target dev .
docker compose up -d runner  # launches the main service defined in compose
```

* Use a multi-stage Dockerfile with a `dev` stage that installs development-only
  tools (linters, debugpy, etc.).  
* `runner` service in compose still mounts `.:/workspace` so Python edits are
  instant.

### 2.2 When to Choose
• You often tweak system-level packages (e.g. `apt-get install g++`) and want a
  reproducible image after each change.  
• CI pipelines build the *exact* `ntplatform:dev` tag and run unit tests inside
  it.

### 2.3 Performance Tips
* Use BuildKit layer caching and keep `requirements.txt` close to the top of the
  Dockerfile so simple code edits don't invalidate heavy apt/PyPI layers.
* Run tests with `pytest -n auto` to exploit multi-core CPUs inside the
  container.

---
## 3. Quick Decision Matrix

| Requirement                                | Option 2 | Option 3 |
|--------------------------------------------|:--------:|:--------:|
| Need to compile C-extensions frequently     |   ✓✓     |   ✓✓✓    |
| Team wants *identical* env across machines |   ✓✓✓    |   ✓✓✓    |
| Fast inner loop for pure-Python edits       |   ✓✓✓    |   ✓✓     |
| Minimal Docker knowledge required          |   ✓✓     |   ✓      |

---
**Next steps**
1. Copy the compose snippet above into `docker/docker-compose.yml` (or create a
   separate `docker-compose.dev.yml`).
2. Add `make devshell` target: `docker compose up -d devshell && docker exec -it devshell bash`.
3. Try attaching Cursor to the container and running `pytest -q` to verify the
   bind-mount path. 