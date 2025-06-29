from setup_path import *  # This should be the first import

try:
    from nautilus_trader.persistence import *

    print("Successfully imported nautilus_trader.persistence")
except ImportError as e:
    print(f"Error importing nautilus_trader.persistence: {e}")
    print("\nTrying alternative import...")
    try:
        import nautilus_trader

        print(f"Nautilus Trader version: {nautilus_trader.__version__}")
    except ImportError as e:
        print(f"Error importing nautilus_trader: {e}")
