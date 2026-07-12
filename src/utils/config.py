"""
Config Loader — Carga toda la configuración YAML en un dict accesible.

Uso:
    from src.utils.config import get_config
    cfg = get_config()
    print(cfg.broker.account.type)  # 'demo'
    print(cfg.strategy.mean_reversion.rsi.period)  # 14
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional
import yaml
import os


_CONFIG_CACHE: Optional[dict] = None
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_CONFIG_FILES = [
    "broker.yaml",
    "strategy.yaml",
    "risk.yaml",
    "telegram.yaml",
    "paths.yaml",
    "agents.yaml",
    "learning.yaml",
]


class ConfigDict(dict):
    """Dict que permite acceso por atributo: cfg.key.subkey"""
    def __getattr__(self, key):
        try:
            val = self[key]
            if isinstance(val, dict):
                return ConfigDict(val)
            return val
        except KeyError:
            raise AttributeError(f"Config has no key '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


def load_config(reload: bool = False) -> ConfigDict:
    """Carga toda la configuración desde los archivos YAML en config/"""
    global _CONFIG_CACHE

    if _CONFIG_CACHE is not None and not reload:
        return ConfigDict(_CONFIG_CACHE)

    config = {}

    for filename in _CONFIG_FILES:
        section = filename.replace(".yaml", "")
        filepath = _CONFIG_DIR / filename
        if not filepath.exists():
            print(f"⚠️  Config file not found: {filename} — skipping")
            continue
        with open(filepath) as f:
            data = yaml.safe_load(f)
            if data:
                # Si el YAML tiene una clave raíz que coincide con el nombre,
                # la usamos directamente; si no, usamos todo el dict
                if isinstance(data, dict) and section in data:
                    config[section] = data[section]
                else:
                    config[section] = data

    # Cargar variables de entorno como override
    env_overrides = {
        "MT5_LOGIN": ("broker", "mt5", "login"),
        "MT5_PASSWORD": ("broker", "mt5", "password"),
        "MT5_SERVER": ("broker", "mt5", "server"),
        "TELEGRAM_BOT_TOKEN": ("telegram", "bot_token"),
    }
    for env_var, keys in env_overrides.items():
        val = os.getenv(env_var)
        if val:
            target = config
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            target[keys[-1]] = int(val) if val.isdigit() and env_var == "MT5_LOGIN" else val

    _CONFIG_CACHE = config
    return ConfigDict(config)


def get_config(reload: bool = False) -> ConfigDict:
    """Alias para load_config"""
    return load_config(reload)


def save_config_section(section: str, data: dict) -> None:
    """Guarda una sección de config de vuelta a su archivo YAML"""
    filename = f"{section}.yaml"
    filepath = _CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config section '{section}' not found at {filepath}")
    with open(filepath, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    # Invalidar cache
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    print(f"✅ Config '{filename}' saved")


def reload_config() -> ConfigDict:
    """Recarga toda la configuración desde disco"""
    return load_config(reload=True)