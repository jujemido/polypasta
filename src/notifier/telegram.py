"""
Telegram Notifier — Envía notificaciones de trades, errores y resúmenes.

Configuración en config/telegram.yaml.
Desactivar: telegram.enabled = false
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os

try:
    import telegram
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class TelegramNotifier:
    """Notificador vía Telegram"""

    def __init__(self, config: dict):
        self.cfg = config["telegram"]
        self.enabled = self.cfg.get("enabled", False)
        self.format_cfg = self.cfg.get("format", {})
        self.notif_cfg = self.cfg.get("notifications", {})

        self._bot = None
        self._chat_ids = self.cfg.get("chat_ids", [])

        if not self.enabled:
            print("📵 Telegram notifications disabled")
            return

        if not TELEGRAM_AVAILABLE:
            print("⚠️  python-telegram-bot not installed. pip install python-telegram-bot")
            self.enabled = False
            return

        token = self.cfg.get("bot_token", "")
        if not token:
            print("⚠️  Telegram bot_token not configured")
            self.enabled = False
            return

        self._bot = telegram.Bot(token=token)

    def _send(self, text: str):
        """Envía mensaje a todos los chats configurados"""
        if not self.enabled or not self._bot:
            return

        for chat_id in self._chat_ids:
            try:
                self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception as e:
                print(f"❌ Telegram send error (chat {chat_id}): {e}")

    def _fmt(self, text: str) -> str:
        """Aplica formato según config"""
        if self.format_cfg.get("emoji", True):
            pass  # Ya incluimos emojis en los textos
        return text

    # ─────────────────────────────────────────────
    # Notifications
    # ─────────────────────────────────────────────

    def notify_startup(self, mode: str, strategy: str):
        """Bot iniciado"""
        if not self.notif_cfg.get("startup", True):
            return
        text = (
            f"🤖 <b>PolypastaBot iniciado</b>\n"
            f"📋 Modo: {mode}\n"
            f"📊 Estrategia: {strategy}\n"
            f"🕐 {datetime.now():%d/%m %H:%M}"
        )
        self._send(self._fmt(text))

    def notify_trade_open(self, symbol: str, action: str, price: float,
                          volume: float, sl: float, tp: float, reason: str):
        """Trade abierto"""
        if not self.notif_cfg.get("trade_open", True):
            return
        emoji = "🟢" if action == "buy" else "🔴"
        text = (
            f"{emoji} <b>TRADE OPEN</b>\n"
            f"📈 {symbol}\n"
            f"{'BUY' if action == 'buy' else 'SELL'} @ {price:.2f}\n"
            f"📦 Vol: {volume}\n"
            f"🛑 SL: {sl:.2f}\n"
            f"🎯 TP: {tp:.2f}\n"
            f"💡 {reason}"
        )
        self._send(self._fmt(text))

    def notify_trade_close(self, symbol: str, action: str, entry: float,
                           exit_price: float, profit: float, reason: str):
        """Trade cerrado"""
        if not self.notif_cfg.get("trade_close", True):
            return
        emoji = "✅" if profit > 0 else "❌"
        pct = ((exit_price - entry) / entry) * 100 if action == "buy" else ((entry - exit_price) / entry) * 100
        text = (
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"📈 {symbol}\n"
            f"💰 P&L: {profit:+.2f} ({pct:+.2f}%)\n"
            f"💡 {reason}"
        )
        self._send(self._fmt(text))

    def notify_error(self, error: str, context: Optional[str] = None):
        """Error del bot"""
        if not self.notif_cfg.get("error", True):
            return
        text = (
            f"⚠️ <b>Bot Error</b>\n"
            f"{error}\n"
        )
        if context:
            text += f"📋 {context}"
        self._send(self._fmt(text))

    def notify_drawdown(self, dd_pct: float, limit: float):
        """Alerta de drawdown"""
        if not self.notif_cfg.get("drawdown_alert", True):
            return
        text = (
            f"🚨 <b>DRAWDOWN ALERT</b>\n"
            f"📉 Current: {dd_pct:.1%}\n"
            f"⚠️ Limit: {limit:.0%}"
        )
        self._send(self._fmt(text))

    def notify_daily_summary(self, metrics: dict, trades: list):
        """Resumen diario"""
        if not self.notif_cfg.get("daily_summary", True):
            return
        pnl = metrics.get("total_pnl", 0)
        emoji = "📈" if pnl >= 0 else "📉"
        text = (
            f"{emoji} <b>Resumen Diario</b>\n"
            f"┌{'─'*30}┐\n"
            f"Balance: ${metrics.get('current_balance', 0):.2f}\n"
            f"P&L Total: {pnl:+.2f}\n"
            f"Trades hoy: {metrics.get('daily_trades', 0)}\n"
            f"Win Rate: {metrics.get('win_rate', 0):.0%}\n"
            f"Drawdown: {metrics.get('current_drawdown', 0):.1%}\n"
            f"Posiciones: {metrics.get('open_positions', 0)}\n"
            f"└{'─'*30}┘"
        )
        self._send(self._fmt(text))

    def notify_weekly_summary(self, metrics: dict):
        """Resumen semanal"""
        if not self.notif_cfg.get("weekly_summary", True):
            return
        pnl = metrics.get("total_pnl", 0)
        emoji = "📈" if pnl >= 0 else "📉"
        text = (
            f"{emoji} <b>Resumen Semanal</b>\n"
            f"Balance: ${metrics.get('current_balance', 0):.2f}\n"
            f"P&L: {pnl:+.2f}\n"
            f"Trades: {metrics.get('total_trades', 0)}\n"
            f"Win Rate: {metrics.get('win_rate', 0):.0%}\n"
            f"Drawdown: {metrics.get('current_drawdown', 0):.1%}"
        )
        self._send(self._fmt(text))

    def send_message(self, text: str):
        """Envía mensaje libre"""
        self._send(self._fmt(text))