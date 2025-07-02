from scripts.paper_trading.run_paper_trading_daemon import main

if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(main()))
