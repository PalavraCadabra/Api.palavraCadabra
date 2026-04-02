import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


class LanguageExpansionService:
    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def expand(self, symbols: list[str], context: dict | None = None) -> dict:
        """
        Expand telegraphic AAC sequence to natural Portuguese.

        Input:  ["eu", "querer", "água", "frio"]
        Output: {
            "expanded": "Eu quero água gelada, por favor.",
            "alternatives": [
                "Eu gostaria de água fria.",
                "Posso beber água gelada?"
            ],
            "explanation": "Conjugou 'querer' para primeira pessoa ..."
        }
        """
        prompt = f"""Você é um assistente de comunicação aumentativa e alternativa (CAA) para pessoas não verbais no Brasil.

O usuário selecionou estes símbolos em sequência: {' '.join(symbols)}

Sua tarefa:
1. Expanda essa sequência telegráfica em uma frase gramaticalmente correta em português brasileiro
2. Mantenha a intenção original do usuário
3. Seja natural — como uma pessoa falaria
4. Forneça 2 alternativas com diferentes tons/formalidades
5. Explique brevemente as transformações gramaticais feitas

{"Contexto adicional: " + json.dumps(context, ensure_ascii=False) if context else ""}

Responda em JSON com este formato exato:
{{
    "expanded": "frase principal expandida",
    "alternatives": ["alternativa 1", "alternativa 2"],
    "explanation": "explicação breve das transformações"
}}"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
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
            return {"expanded": text, "alternatives": [], "explanation": ""}
