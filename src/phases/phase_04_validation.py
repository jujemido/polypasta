"""
Phase 4: Validation — AI Validator revisa la señal antes de ejecutar.
"""
from typing import Optional


class PhaseValidation:
    """Valida la señal con IA antes de ejecutar (opcional)"""

    def __init__(self, ai_validator):
        self.ai_validator = ai_validator

    def execute(self, ctx: dict, action: dict) -> dict:
        """
        Valida la señal con el AI Validator.

        Returns:
            {"approved": True} o {"blocked": True, "reason": "..."}
        """
        if not self.ai_validator.enabled:
            return {"approved": True}

        decision = self.ai_validator.validate(action)
        ctx["validation"] = decision
        return decision