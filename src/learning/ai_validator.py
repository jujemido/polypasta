"""
AI Validator — Valida señales de trading usando IA (OpenRouter/DeepSeek).
Antes de ejecutar un trade, pregunta a la IA si la operación tiene sentido.

Si la IA bloquea → no se ejecuta → se crea log con el motivo
Si la IA aprueba → se ejecuta → se crea log con la aprobación
"""

import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AIValidator:
    """
    Valida señales de trading usando IA.

    Lee la API key de OPENROUTER_API_KEY del entorno o de learning.yaml.
    """

    def __init__(self, config: dict):
        lcfg = config.get("learning", {}).get("ai_validator", {})
        self.enabled = lcfg.get("enabled", False)

        if not self.enabled:
            print("🤖 AI Validator: desactivado")
            return

        self.api_key = lcfg.get("api_key") or os.getenv("OPENROUTER_API_KEY", "")
        self.model = lcfg.get("model", "deepseek/deepseek-v4-flash")
        self.api_base = lcfg.get("api_base", "https://openrouter.ai/api/v1")
        self.thresholds = lcfg.get("thresholds", {})
        self.system_prompt = lcfg.get("prompts", {}).get("system", "")

        if not self.api_key:
            print("⚠️  AI Validator: no hay API key. Desactivando.")
            self.enabled = False
            return

        if not REQUESTS_AVAILABLE:
            print("⚠️  AI Validator: requests no instalado. pip install requests")
            self.enabled = False
            return

        print(f"🤖 AI Validator: activo ({self.model})")

    # ─────────────────────────────────────────────
    # Validación de una señal
    # ─────────────────────────────────────────────

    def validate(
        self,
        agent_name: str,
        symbol: str,
        action: str,
        confidence: float,
        price: float,
        reason: str,
        indicators: Dict[str, Any],
        market_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Valida una señal con la IA.

        Args:
            agent_name: Nombre del agente
            symbol: Símbolo a operar
            action: buy/sell
            confidence: Confianza del agente (0-1)
            price: Precio actual
            reason: Razón de la señal
            indicators: Dict de indicadores técnicos actuales
            market_context: Contexto adicional del mercado

        Returns:
            {"decision": "approve"|"block", "confidence": float,
             "reason": str, "validated": bool}
        """
        if not self.enabled:
            return {"decision": "approve", "confidence": 1.0,
                    "reason": "AI Validator desactivado", "validated": False}

        # Construir prompt
        user_message = self._build_prompt(
            agent_name, symbol, action, confidence, price, reason, indicators, market_context
        )

        try:
            response = self._call_api(user_message)
            result = self._parse_response(response)
            return result
        except Exception as e:
            print(f"⚠️  AI Validator error: {e}")
            # Si falla la IA, NO bloquear (fail open)
            return {"decision": "approve", "confidence": 0.5,
                    "reason": f"AI Validator error: {e}", "validated": False}

    # ─────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────

    def _build_prompt(
        self, agent_name, symbol, action, confidence, price, reason, indicators, market_context
    ) -> str:
        """Construye el prompt para la IA"""
        ind_text = json.dumps(indicators, indent=2, default=str)
        prompt = f"""
AGENTE: {agent_name}
SÍMBOLO: {symbol}
ACCIÓN: {action.upper()}
PRECIO: ${price:.2f}
CONFIANZA DEL AGENTE: {confidence:.0%}
RAZÓN TÉCNICA: {reason}

INDICADORES ACTUALES:
{ind_text}

{"CONTEXTO ADICIONAL: " + market_context if market_context else ""}

¿Apruebas o bloqueas esta operación?
Responde SOLO con JSON: {"decision": "approve"|"block", "confidence": 0.0-1.0, "reason": "..."}
"""
        return prompt.strip()

    def _call_api(self, user_message: str) -> Dict:
        """Llama a la API de OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,  # Baja temperatura = más determinista
            "max_tokens": 256,
        }

        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def _parse_response(self, response: Dict) -> Dict[str, Any]:
        """Parsea la respuesta JSON de la IA"""
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Extraer JSON de la respuesta
        try:
            # Buscar JSON entre llaves
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            # Fallback: buscar palabras clave
            content_lower = content.lower()
            decision = "approve" if "approve" in content_lower else "block"
            result = {
                "decision": decision,
                "confidence": 0.5,
                "reason": content[:200],
            }

        # Normalizar
        result["validated"] = True
        result["confidence"] = min(1.0, max(0.0, float(result.get("confidence", 0.5))))

        return result


class AIValidatorResult:
    """Resultado de una validación IA, formateado para logs"""

    @staticmethod
    def to_log_entry(result: Dict, agent_id: str, agent_name: str,
                     symbol: str, action: str) -> Dict:
        """Convierte resultado a entrada de log para dashboard"""
        return {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "agent_name": agent_name,
            "symbol": symbol,
            "action_requested": action,
            "ai_decision": result.get("decision", "approve"),
            "ai_confidence": result.get("confidence", 1.0),
            "ai_reason": result.get("reason", ""),
            "ai_validated": result.get("validated", False),
        }