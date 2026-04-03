"""
Seed do banco de dados com atividades de alfabetizacao (templates).

Uso:
    python -m scripts.seed_literacy_activities
"""

import asyncio

from sqlalchemy import select, func

from app.database import engine, async_session_factory
from app.models.literacy_activity import LiteracyActivity, ActivityType
from app.models.literacy_program import LiteracyStage

SEED_ACTIVITIES = [
    # ── Stage 1 — Foundations ──
    {
        "activity_type": ActivityType.symbol_matching,
        "stage": LiteracyStage.foundations,
        "title": "Parear: Animais",
        "description": "Parear simbolos de animais com as palavras faladas correspondentes.",
        "difficulty_level": 1,
        "estimated_duration_minutes": 5,
        "content": {
            "pairs": [
                {"symbol_label": "gato", "word": "gato", "audio_hint": "ga-to"},
                {"symbol_label": "cachorro", "word": "cachorro", "audio_hint": "ca-chor-ro"},
                {"symbol_label": "passaro", "word": "passaro", "audio_hint": "pas-sa-ro"},
                {"symbol_label": "peixe", "word": "peixe", "audio_hint": "pei-xe"},
            ],
            "instructions": "Toque no simbolo que corresponde a palavra que voce ouviu.",
        },
    },
    {
        "activity_type": ActivityType.letter_recognition,
        "stage": LiteracyStage.foundations,
        "title": "Conhecer as Letras",
        "description": "Identificar letras do alfabeto apresentadas visualmente.",
        "difficulty_level": 1,
        "estimated_duration_minutes": 5,
        "content": {
            "letters": ["A", "B", "C", "D", "E"],
            "target": "A",
            "instructions": "Encontre a letra A entre as opcoes.",
            "rounds": [
                {"target": "A", "options": ["A", "B", "C", "D"]},
                {"target": "E", "options": ["B", "E", "D", "C"]},
                {"target": "C", "options": ["A", "D", "C", "B"]},
            ],
        },
    },
    {
        "activity_type": ActivityType.phonological_awareness,
        "stage": LiteracyStage.foundations,
        "title": "Rimas",
        "description": "Identificar palavras que rimam entre si.",
        "difficulty_level": 2,
        "estimated_duration_minutes": 5,
        "content": {
            "rounds": [
                {"word": "gato", "options": ["pato", "mesa", "bola"], "correct": "pato"},
                {"word": "mao", "options": ["pe", "chao", "sol"], "correct": "chao"},
                {"word": "bola", "options": ["cola", "casa", "flor"], "correct": "cola"},
            ],
            "instructions": "Qual palavra rima com a palavra apresentada?",
        },
    },
    {
        "activity_type": ActivityType.print_awareness,
        "stage": LiteracyStage.foundations,
        "title": "Simbolos tem significado",
        "description": "Entender que simbolos e textos representam objetos e ideias reais.",
        "difficulty_level": 1,
        "estimated_duration_minutes": 5,
        "content": {
            "items": [
                {"symbol_label": "agua", "real_object": "copo de agua", "text": "AGUA"},
                {"symbol_label": "comida", "real_object": "prato de comida", "text": "COMIDA"},
                {"symbol_label": "brincar", "real_object": "crianca brincando", "text": "BRINCAR"},
            ],
            "instructions": "Relacione o simbolo com o que ele representa no mundo real.",
        },
    },
    # ── Stage 2 — Emerging ──
    {
        "activity_type": ActivityType.letter_sound,
        "stage": LiteracyStage.emerging,
        "title": "Letra e Som: Vogais",
        "description": "Associar as vogais aos seus sons correspondentes.",
        "difficulty_level": 2,
        "estimated_duration_minutes": 5,
        "content": {
            "letters": [
                {"letter": "A", "sound_hint": "ah", "example_word": "abelha"},
                {"letter": "E", "sound_hint": "eh", "example_word": "elefante"},
                {"letter": "I", "sound_hint": "ee", "example_word": "igloo"},
                {"letter": "O", "sound_hint": "oh", "example_word": "ovo"},
                {"letter": "U", "sound_hint": "oo", "example_word": "uva"},
            ],
            "instructions": "Ouca o som e escolha a vogal correspondente.",
        },
    },
    {
        "activity_type": ActivityType.sight_words,
        "stage": LiteracyStage.emerging,
        "title": "Palavras do Dia",
        "description": "Aprender palavras de alta frequencia por reconhecimento visual.",
        "difficulty_level": 2,
        "estimated_duration_minutes": 5,
        "content": {
            "words": [
                {"word": "eu", "symbol_label": "eu"},
                {"word": "voce", "symbol_label": "voce"},
                {"word": "sim", "symbol_label": "sim"},
                {"word": "nao", "symbol_label": "nao"},
                {"word": "quero", "symbol_label": "quero"},
            ],
            "instructions": "Leia a palavra e toque no simbolo correspondente.",
        },
    },
    {
        "activity_type": ActivityType.shared_reading,
        "stage": LiteracyStage.emerging,
        "title": "Leitura com CAA",
        "description": "Leitura compartilhada de historia curta com suporte de simbolos CAA.",
        "difficulty_level": 2,
        "estimated_duration_minutes": 10,
        "content": {
            "story": {
                "title": "O Gato e o Peixe",
                "pages": [
                    {
                        "text": "O gato viu o peixe.",
                        "symbols": ["gato", "ver", "peixe"],
                    },
                    {
                        "text": "O gato queria o peixe.",
                        "symbols": ["gato", "querer", "peixe"],
                    },
                    {
                        "text": "O peixe nadou rapido.",
                        "symbols": ["peixe", "nadar", "rapido"],
                    },
                ],
            },
            "comprehension_questions": [
                {"question": "Quem viu o peixe?", "options": ["gato", "cachorro"], "correct": "gato"},
                {"question": "O que o peixe fez?", "options": ["nadou", "dormiu"], "correct": "nadou"},
            ],
            "instructions": "Leia a historia com o terapeuta. Toque nos simbolos enquanto le.",
        },
    },
    # ── Stage 3 — Developing ──
    {
        "activity_type": ActivityType.word_decoding,
        "stage": LiteracyStage.developing,
        "title": "Decodificar: Silabas",
        "description": "Ler silabas simples combinando consoantes e vogais.",
        "difficulty_level": 3,
        "estimated_duration_minutes": 5,
        "content": {
            "syllables": [
                {"syllable": "CA", "sound_hint": "kah"},
                {"syllable": "DA", "sound_hint": "dah"},
                {"syllable": "MA", "sound_hint": "mah"},
                {"syllable": "PA", "sound_hint": "pah"},
                {"syllable": "BA", "sound_hint": "bah"},
            ],
            "exercises": [
                {"word": "MALA", "syllables": ["MA", "LA"], "symbol_label": "mala"},
                {"word": "BOLA", "syllables": ["BO", "LA"], "symbol_label": "bola"},
                {"word": "CASA", "syllables": ["CA", "SA"], "symbol_label": "casa"},
            ],
            "instructions": "Junte as silabas para formar a palavra e encontre o simbolo correspondente.",
        },
    },
    {
        "activity_type": ActivityType.sentence_building,
        "stage": LiteracyStage.developing,
        "title": "Montar Frases",
        "description": "Organizar palavras para formar frases com sentido.",
        "difficulty_level": 3,
        "estimated_duration_minutes": 5,
        "content": {
            "exercises": [
                {
                    "words_shuffled": ["gato", "O", "come", "."],
                    "correct_order": ["O", "gato", "come", "."],
                    "symbols": ["gato", "comer"],
                },
                {
                    "words_shuffled": ["bola", "A", "bonita", "e", "."],
                    "correct_order": ["A", "bola", "e", "bonita", "."],
                    "symbols": ["bola", "bonito"],
                },
                {
                    "words_shuffled": ["quero", "Eu", "agua", "."],
                    "correct_order": ["Eu", "quero", "agua", "."],
                    "symbols": ["eu", "querer", "agua"],
                },
            ],
            "instructions": "Arraste as palavras para formar uma frase correta.",
        },
    },
    {
        "activity_type": ActivityType.symbol_to_text,
        "stage": LiteracyStage.developing,
        "title": "Do Simbolo ao Texto",
        "description": "Fazer a ponte entre simbolos CAA e a palavra escrita correspondente.",
        "difficulty_level": 3,
        "estimated_duration_minutes": 5,
        "content": {
            "pairs": [
                {"symbol_label": "comer", "written_word": "COMER"},
                {"symbol_label": "beber", "written_word": "BEBER"},
                {"symbol_label": "dormir", "written_word": "DORMIR"},
                {"symbol_label": "brincar", "written_word": "BRINCAR"},
                {"symbol_label": "escola", "written_word": "ESCOLA"},
            ],
            "instructions": "Toque no simbolo e depois encontre a palavra escrita correspondente.",
        },
    },
    # ── Stage 4 — Conventional ──
    {
        "activity_type": ActivityType.independent_reading,
        "stage": LiteracyStage.conventional,
        "title": "Ler Sozinho",
        "description": "Leitura independente de textos curtos adaptados.",
        "difficulty_level": 4,
        "estimated_duration_minutes": 10,
        "content": {
            "text": "Maria foi ao parque. Ela viu muitas flores. As flores eram bonitas. Maria ficou feliz.",
            "comprehension_questions": [
                {
                    "question": "Onde Maria foi?",
                    "options": ["parque", "escola", "casa"],
                    "correct": "parque",
                },
                {
                    "question": "O que Maria viu?",
                    "options": ["flores", "animais", "carros"],
                    "correct": "flores",
                },
                {
                    "question": "Como Maria ficou?",
                    "options": ["feliz", "triste", "com medo"],
                    "correct": "feliz",
                },
            ],
            "instructions": "Leia o texto e responda as perguntas.",
        },
    },
    {
        "activity_type": ActivityType.functional_writing,
        "stage": LiteracyStage.conventional,
        "title": "Escrever Mensagem",
        "description": "Compor uma mensagem simples usando texto e simbolos como apoio.",
        "difficulty_level": 4,
        "estimated_duration_minutes": 10,
        "content": {
            "prompt": "Escreva uma mensagem para um amigo contando o que voce fez hoje.",
            "word_bank": ["oi", "hoje", "eu", "fui", "brinquei", "comi", "gostei", "tchau"],
            "symbol_support": True,
            "min_words": 3,
            "instructions": "Use as palavras do banco ou digite suas proprias palavras para escrever a mensagem.",
        },
    },
]


async def seed_activities():
    async with async_session_factory() as session:
        # Check existing count
        count_result = await session.execute(
            select(func.count()).select_from(LiteracyActivity).where(
                LiteracyActivity.is_template.is_(True)
            )
        )
        existing_count = count_result.scalar() or 0

        if existing_count > 0:
            print(f"Found {existing_count} existing template activities. Skipping seed.")
            return

        for activity_data in SEED_ACTIVITIES:
            activity = LiteracyActivity(
                is_template=True,
                created_by=None,
                symbol_ids=None,
                **activity_data,
            )
            session.add(activity)

        await session.commit()
        print(f"Seeded {len(SEED_ACTIVITIES)} literacy activities successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_activities())
