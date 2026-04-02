import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


class BoardGenerationService:
    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_board(
        self,
        profile: dict,
        board_type: str = "personal",
        context: str = "geral",
        available_symbols: list[dict] | None = None,
    ) -> dict:
        """
        Generate a personalized board layout.

        Returns:
        {
            "name": "Prancha - Hora do Lanche",
            "grid_rows": 4,
            "grid_cols": 5,
            "cells": [
                {"row": 0, "col": 0, "label": "eu", "grammatical_class": "pronoun"},
                ...
            ],
            "rationale": "Explanation of why these symbols were chosen"
        }
        """
        symbol_list = ""
        if available_symbols:
            by_class: dict[str, list[str]] = {}
            for s in available_symbols:
                cls = s.get("grammatical_class", "misc")
                by_class.setdefault(cls, []).append(s["label_pt"])
            symbol_list = "\n".join(
                f"- {cls}: {', '.join(labels[:30])}" for cls, labels in by_class.items()
            )

        prompt = f"""Você é um especialista em CAA (Comunicação Aumentativa e Alternativa) e fonoaudiologia.

Crie uma prancha de comunicação personalizada.

PERFIL DO USUÁRIO:
- Nome: {profile.get('name', 'Usuário')}
- Nível comunicativo: {profile.get('communication_level', 'symbolic')}
- Capacidade motora: {profile.get('motor_capability', 'full_touch')}
- Contexto: {context}
- Tipo de prancha: {board_type}

{f"SÍMBOLOS DISPONÍVEIS:{chr(10)}{symbol_list}" if symbol_list else ""}

REGRAS:
1. Siga o padrão Fitzgerald Key: pronomes=amarelo, verbos=verde, adjetivos=azul, substantivos=laranja, social=rosa, perguntas=ciano
2. Palavras-núcleo (core vocabulary) nas primeiras posições
3. Posições consistentes para planejamento motor
4. Grade adequada ao nível motor: full_touch=4x5 ou 6x8, limited_touch=3x4, switch_scanning=2x3
5. Símbolos relevantes para o contexto "{context}"
6. Use APENAS símbolos da lista de disponíveis quando fornecida

Responda em JSON:
{{
    "name": "nome da prancha",
    "grid_rows": N,
    "grid_cols": N,
    "cells": [
        {{"row": 0, "col": 0, "label": "palavra", "grammatical_class": "class"}},
        ...
    ],
    "rationale": "explicação das escolhas"
}}"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError("Failed to parse board generation response")
