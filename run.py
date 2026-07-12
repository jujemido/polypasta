"""
PolypastaBot — Algo Trading Bot Multi-Agente
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.config import get_config
from src.core.engine import TradingEngine


def main():
    cfg = get_config()
    engine = TradingEngine(cfg)

    try:
        interval = 15
        for arg in sys.argv:
            if arg.startswith("--interval="):
                interval = int(arg.split("=")[1])
        engine.run(interval_minutes=interval)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()