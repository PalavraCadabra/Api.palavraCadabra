import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


class ClinicalInsightsService:
    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_insights(
        self,
        profile: dict,
        usage_summary: dict,
        recent_sessions: list[dict],
    ) -> dict:
        """
        Generate clinical insights from usage data.

        Returns a structured clinical report with summary, communication profile,
        vocabulary analysis, session recommendations, milestones, and alerts.
        """
        prompt = f"""Você é um fonoaudiólogo especialista em CAA (Comunicação Aumentativa e Alternativa) analisando dados de uso de um paciente.

PERFIL DO PACIENTE:
- Nome: {profile.get('name')}
- Nível comunicativo: {profile.get('communication_level')}
- Capacidade motora: {profile.get('motor_capability')}

DADOS DE USO (período de análise):
- Total de símbolos selecionados: {usage_summary.get('total_symbols_selected', 0)}
- Símbolos únicos utilizados: {usage_summary.get('unique_symbols_used', 0)}
- Razão tipo-token (TTR): {usage_summary.get('ttr', 0):.2f}
- Comprimento médio de mensagem (MLU): {usage_summary.get('avg_message_length', 0):.1f}
- Taxa comunicativa: {usage_summary.get('communication_rate', 0):.1f} símbolos/min
- Sessões no período: {usage_summary.get('session_count', 0)}

DISTRIBUIÇÃO POR CLASSE GRAMATICAL:
{json.dumps(usage_summary.get('grammatical_class_distribution', {}), indent=2, ensure_ascii=False)}

SÍMBOLOS MAIS USADOS:
{json.dumps(usage_summary.get('top_symbols', [])[:20], indent=2, ensure_ascii=False)}

USO DIÁRIO:
{json.dumps(usage_summary.get('daily_usage', [])[-14:], indent=2, ensure_ascii=False)}

{f"SESSÕES RECENTES:{chr(10)}{json.dumps(recent_sessions[:5], indent=2, ensure_ascii=False)}" if recent_sessions else ""}

Gere um relatório clínico completo em JSON:
{{
    "summary": "Resumo de 2-3 frases do progresso geral",
    "communication_profile": {{
        "strengths": ["pontos fortes observados"],
        "areas_for_growth": ["áreas que precisam de atenção"],
        "communication_stage": "estágio atual estimado"
    }},
    "vocabulary_analysis": {{
        "diversity": "análise da diversidade vocabular",
        "gaps": ["classes ou categorias sub-representadas"],
        "recommendations": ["novos símbolos/categorias a introduzir"]
    }},
    "session_recommendations": [
        {{
            "focus": "foco da sessão",
            "activities": ["atividades sugeridas"],
            "goals": ["metas mensuráveis"]
        }}
    ],
    "milestones": {{
        "achieved": ["marcos atingidos"],
        "next_targets": ["próximos marcos a buscar"]
    }},
    "alerts": ["alertas ou preocupações, se houver"]
}}"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
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
            return {"summary": text, "error": "Failed to parse structured response"}
