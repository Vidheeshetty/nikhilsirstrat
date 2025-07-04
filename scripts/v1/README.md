# Scripts Package Overview

This directory contains **CLI utilities**, **helper scripts**, and **deployment assets** used during development and operations.

```
scripts/
├── backtesting/        # Back-test runners (single & batch)
├── data_import/        # CSV→Parquet converters and helpers
├── paper_trading/      # Live / paper-trading engine, daemon & web server
├── deploy/             # Deployment shell scripts
└── *.py                # Thin compatibility shims (maintain old paths)
```

Highlights
-----------
1. **backtesting/**
   • `run_backtest.py` – run a single-instrument back-test.  
   • `run_batch_backtest.py` – batch runner for multiple instruments.

2. **data_import/**
   • `csv_to_parquet_converter.py` – generic converter driven by YAML config.  
   • `check_catalog_status.py` – skips redundant conversions by timestamp.  
   • `smart_convert.py` – wrapper that first calls the checker, then the converter.

3. **paper_trading/**
   • `run_paper_trading.py` – interactive paper-trading engine.  
   • `run_paper_trading_daemon.py` – daemonised background version with health-checks.  
   • `paper_trading_server.py` – FastAPI web dashboard/API.  
   • `setup_paper_trading.py` – one-shot helper to scaffold configs & folders.

4. **deploy/**
   • `deploy_server.sh` – local Docker compose deployment.  
   • `deploy_to_server.sh` – SSH / rsync based remote deployment script.

Legacy shims
------------
Thin wrapper files remain at the old locations (`scripts/run_backtest.py`, `scripts/run_paper_trading.py`, etc.). They simply import & execute the relocated modules so existing documentation and CI calls continue to work. These will be removed in a future breaking-change release.

Removed / deprecated
--------------------
• `convert_all.sh`, `run_parquet_builder.py`, `csv_to_parquet_converter.py` (shim) – superseded by tools in `data_import/`. 