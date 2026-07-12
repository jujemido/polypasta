"""
File utils — Utilidades para manejo de archivos y logging.
"""

import os
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def ensure_dir(path: str) -> Path:
    """Crea directorio si no existe"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_trade(
    filepath: str,
    trade_data: Dict[str, Any],
):
    """Añade un trade al CSV de trades"""
    ensure_dir(os.path.dirname(filepath))

    file_exists = os.path.exists(filepath)
    fieldnames = [
        "timestamp", "symbol", "action", "volume", "price",
        "sl", "tp", "profit", "commission", "swap",
        "balance_after", "strategy", "reason", "ticket",
    ]

    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(trade_data)


def log_error(filepath: str, error: str, context: Optional[Dict] = None):
    """Log de errores"""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "a") as f:
        ts = datetime.now().isoformat()
        ctx = f" | {json.dumps(context)}" if context else ""
        f.write(f"[{ts}] ERROR: {error}{ctx}\n")


def log_performance(filepath: str, metrics: Dict[str, Any]):
    """Actualiza métricas de rendimiento en JSON"""
    ensure_dir(os.path.dirname(filepath))

    existing = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = {}

    # Merge con nuevo
    existing["last_updated"] = datetime.now().isoformat()
    for k, v in metrics.items():
        existing[k] = v

    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2, default=str)


def read_trades(filepath: str) -> List[Dict]:
    """Lee el CSV de trades"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline="") as f:
        return list(csv.DictReader(f))


def read_performance(filepath: str) -> Dict:
    """Lee métricas de rendimiento"""
    if not os.path.exists(filepath):
        return {}
    with open(filepath) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}