"""
_____/\\\\\\\\\\\\_______/\\\\\\\\\________/\\\\\\\\\\\__________/\\\\\\\\\________/\\\\\\\\\_____/\\\______________/\\\_
 ___/\\\//////////______/\\\///////\\\____/\\\/////////\\\____/\\\///////\\\____/\\\///////\\\__\/\\\_____________\/\\\_
  __/\\\_______________\/\\\_____\/\\\___\//\\\______\///___/\\\_______\/\\\__\/\\\_______\/\\\__\/\\\_____________\/\\\_
   _\/\\\____/\\\\\\\___\/\\\\\\\\\\\/____\////\\\__________\//\\\______/\\\___\/\\\\\\\\\\\\\\\__\/\\\_____________\/\\\_
    _\/\\\___\/////\\\___\/\\\//////\\\_______\////\\\_______\///\\\\\\\\\/____\/\\\/////////\\\__\/\\\_____________\/\\\_
     _\/\\\_______\/\\\___\/\\\____\//\\\_________\////\\\______/\\\///////\\\___\/\\\_______\/\\\__\/\\\_____________\/\\\_
      _\/\\\_______\/\\\___\/\\\_____\//\\\__/\\\______\//\\\__/\\\_______\/\\\__\/\\\_______\/\\\__\/\\\_____________\/\\\_
       _\//\\\\\\\\\\\\/____\/\\\______\//\\\_\///\\\\\\\\\\\/__\///\\\\\\\\\/___\/\\\_______\/\\\__\/\\\\\\\\\\\\\\\_\/\\\\\\\\\\\\\\\_
        __\////////////______\///________\////____\///////////______\/////////_____\///________\///___\///////////////__\///////////////__

                              PolypastaBot — Algo Trading Bot
                              Multi-Agente | Exness + MT5 + Python
                              v2.0.0
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.config import get_config
from src.core.engine import TradingEngine


def main():
    """Entry point principal"""
    cfg = get_config()

    mode = cfg["broker"]["account"].get("type", "demo")
    multi_agent = "--single" not in sys.argv  # Default multi-agent

    engine = TradingEngine(cfg, multi_agent=multi_agent)

    try:
        if "--backtest" in sys.argv:
            engine.run_backtest()
        else:
            interval = 15  # Multi-agent default
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