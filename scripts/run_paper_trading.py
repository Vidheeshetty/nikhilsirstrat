from scripts.paper_trading.run_paper_trading import main

if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(main()))
