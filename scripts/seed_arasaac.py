"""
Seed do banco de dados com pictogramas ARASAAC (pt-BR).

Busca todos os pictogramas da API ARASAAC em português,
mapeia categorias para classes gramaticais Fitzgerald Key,
e insere no banco de dados.

Uso:
    python -m scripts.seed_arasaac [--core-only] [--limit N]
"""

import argparse
import asyncio
import sys

import httpx
from sqlalchemy import select, func

from app.database import engine, async_session_factory
from app.models.symbol import Symbol, GrammaticalClass

# URL base da API ARASAAC
ARASAAC_API = "https://api.arasaac.org/v1/pictograms/all/pt"
ARASAAC_IMG = "https://static.arasaac.org/pictograms/{id}/{id}_300.png"

# Fitzgerald Key — mapeamento de categorias ARASAAC para classes gramaticais
FITZGERALD_MAP: dict[str, GrammaticalClass] = {
    # Verbos
    "verb": GrammaticalClass.verb,
    "usual verbs": GrammaticalClass.verb,
    # Adjetivos
    "qualifying adjective": GrammaticalClass.adjective,
    # Pronomes
    "pronoun": GrammaticalClass.pronoun,
    "personal pronoun": GrammaticalClass.pronoun,
    "demonstrative": GrammaticalClass.pronoun,
    "possessive": GrammaticalClass.pronoun,
    # Frases sociais
    "social convention": GrammaticalClass.social_phrase,
    "social skill": GrammaticalClass.social_phrase,
    "feeling": GrammaticalClass.social_phrase,
    "emotion": GrammaticalClass.social_phrase,
    # Perguntas
    "question": GrammaticalClass.question,
    "interrogative": GrammaticalClass.question,
}

# Cores Fitzgerald Key por classe gramatical
FITZGERALD_COLORS: dict[GrammaticalClass, str] = {
    GrammaticalClass.pronoun: "#FFEB3B",        # Amarelo — Pessoas/Pronomes
    GrammaticalClass.verb: "#4CAF50",            # Verde — Ações/Verbos
    GrammaticalClass.adjective: "#2196F3",       # Azul — Adjetivos/Advérbios
    GrammaticalClass.noun: "#FF9800",            # Laranja — Substantivos
    GrammaticalClass.social_phrase: "#E91E63",   # Rosa — Frases Sociais
    GrammaticalClass.misc: "#9C27B0",            # Roxo — Diversos
    GrammaticalClass.question: "#00BCD4",        # Ciano — Perguntas
}


def classify_pictogram(categories: list[str]) -> GrammaticalClass:
    """Determina a classe gramatical baseada nas categorias ARASAAC."""
    for cat in categories:
        cat_lower = cat.lower()
        if cat_lower in FITZGERALD_MAP:
            return FITZGERALD_MAP[cat_lower]
    # Default: substantivo (maioria dos pictogramas são objetos/coisas)
    return GrammaticalClass.noun


def pick_category(categories: list[str]) -> str:
    """Escolhe a categoria mais relevante para exibição."""
    # Prioriza categorias de core vocabulary
    for cat in categories:
        if cat.startswith("core vocabulary"):
            return cat
    # Ignora categorias genéricas
    skip = {"verb", "usual verbs", "qualifying adjective", "object"}
    for cat in categories:
        if cat not in skip:
            return cat
    return categories[0] if categories else "misc"


async def fetch_arasaac_pictograms(core_only: bool = False) -> list[dict]:
    """Busca todos os pictogramas da API ARASAAC em português."""
    print(f"Buscando pictogramas ARASAAC (pt)...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(ARASAAC_API)
        response.raise_for_status()
        data = response.json()

    if core_only:
        data = [
            p for p in data
            if any("core vocabulary" in c for c in p.get("categories", []))
            or p.get("aac", False)
        ]
        print(f"  Filtrado para core/AAC: {len(data)} pictogramas")
    else:
        print(f"  Total: {len(data)} pictogramas")

    return data


def pictogram_to_symbol(picto: dict, rank: int | None = None) -> dict:
    """Converte um pictograma ARASAAC para os campos do model Symbol."""
    arasaac_id = picto["_id"]
    categories = picto.get("categories", [])
    keywords_data = picto.get("keywords", [])

    # Label principal: primeiro keyword
    label = keywords_data[0]["keyword"] if keywords_data else f"picto_{arasaac_id}"

    # Todas as keywords como lista de strings
    all_keywords = []
    for kw in keywords_data:
        all_keywords.append(kw["keyword"])
        if kw.get("plural"):
            all_keywords.append(kw["plural"])

    # Classe gramatical e cor Fitzgerald
    gram_class = classify_pictogram(categories)
    fitz_color = FITZGERALD_COLORS[gram_class]

    # Categoria para exibição
    category = pick_category(categories)

    return {
        "arasaac_id": arasaac_id,
        "label_pt": label,
        "category": category,
        "image_url": ARASAAC_IMG.format(id=arasaac_id),
        "grammatical_class": gram_class,
        "fitzgerald_color": fitz_color,
        "frequency_rank": rank,
        "keywords": all_keywords if all_keywords else None,
    }


async def seed(core_only: bool = False, limit: int | None = None) -> None:
    """Executa o seed de pictogramas ARASAAC no banco."""
    # Buscar pictogramas
    pictograms = await fetch_arasaac_pictograms(core_only=core_only)

    if limit:
        pictograms = pictograms[:limit]
        print(f"  Limitado a {limit} pictogramas")

    # Verificar quantos já existem no banco
    async with async_session_factory() as session:
        result = await session.execute(select(func.count(Symbol.id)))
        existing_count = result.scalar_one()
        print(f"  Símbolos já no banco: {existing_count}")

        if existing_count > 0:
            # Pegar IDs ARASAAC existentes para evitar duplicatas
            result = await session.execute(
                select(Symbol.arasaac_id).where(Symbol.arasaac_id.isnot(None))
            )
            existing_ids = {row[0] for row in result.all()}
            pictograms = [p for p in pictograms if p["_id"] not in existing_ids]
            print(f"  Novos pictogramas para inserir: {len(pictograms)}")

        if not pictograms:
            print("  Nada para inserir. Banco já está populado.")
            return

        # Inserir em batches
        batch_size = 500
        total = len(pictograms)
        inserted = 0

        for i in range(0, total, batch_size):
            batch = pictograms[i : i + batch_size]
            symbols = []
            for j, picto in enumerate(batch):
                rank = i + j + 1 if core_only else None
                symbol_data = pictogram_to_symbol(picto, rank=rank)
                symbols.append(Symbol(**symbol_data))

            session.add_all(symbols)
            await session.flush()
            inserted += len(symbols)
            pct = (inserted / total) * 100
            print(f"  Inseridos: {inserted}/{total} ({pct:.0f}%)")

        await session.commit()
        print(f"\nSeed concluído! {inserted} símbolos inseridos no banco.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ARASAAC pictograms")
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Importar apenas pictogramas core vocabulary + AAC-flagged",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limitar número de pictogramas importados",
    )
    args = parser.parse_args()

    asyncio.run(seed(core_only=args.core_only, limit=args.limit))


if __name__ == "__main__":
    main()
