#!/bin/bash
# PolypastaBot Sandbox Runner — para cron job
# Ejecuta un ciclo del bot y deja el dashboard corriendo

cd /Users/jjmillo/Documents/Polypasta
source venv/bin/activate

# Ejecutar un ciclo (dashboard server ya está corriendo en background)
python3 -c "
import sys, os, json
sys.path.insert(0, '.')
from src.utils.config import reload_config
from src.core.engine import TradingEngine

cfg = reload_config()
engine = TradingEngine(cfg, multi_agent=True)
engine.startup()
try:
    # Hasta que se acaben los agentes o timeout
    import signal
    signal.alarm(240)
    engine.run(interval_minutes=0, cycles=1)
except:
    pass
finally:
    engine.shutdown()
    print('Ciclo completado. Dashboard en http://localhost:8050')
" 2>&1