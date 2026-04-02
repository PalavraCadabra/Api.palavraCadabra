"""
Seed de pranchas Core Vocabulary pt-BR.

Baseado na pesquisa de palavras-núcleo (core vocabulary) que compõem
~80% da comunicação diária. Organizado pelo padrão Fitzgerald Key.

Referências:
- Snap Core First (Tobii Dynavox) - ~400 palavras-núcleo
- Banajee, Dicarlo & Stricklin (2003) - Core vocabulary for toddlers
- Van Tatenhove (2009) - Core vocabulary framework
- Pesquisa brasileira: Nunes, Walter (UERJ); Deliberato (UNESP)

Uso:
    python -m scripts.seed_core_boards
"""

import asyncio
import uuid

from sqlalchemy import select

from app.database import engine, async_session_factory
from app.models.board import Board, BoardType
from app.models.board_cell import BoardCell, CellAction
from app.models.symbol import Symbol, GrammaticalClass

# ============================================================
# CORE VOCABULARY pt-BR
# Palavras organizadas por classe gramatical Fitzgerald Key
# ============================================================

CORE_VOCABULARY: dict[str, list[str]] = {
    # PRONOMES (Amarelo #FFEB3B) — Quem
    "pronoun": [
        "eu", "você", "ele", "ela", "nós",
        "eles", "meu", "seu", "isso", "aqui",
        "ali", "este", "aquele",
    ],

    # VERBOS (Verde #4CAF50) — Ações
    "verb": [
        "querer", "ir", "gostar", "comer", "beber",
        "fazer", "ter", "ser", "poder", "precisar",
        "ver", "ouvir", "falar", "brincar", "dormir",
        "ajudar", "dar", "pegar", "abrir", "fechar",
        "colocar", "tirar", "saber", "olhar", "sentir",
        "pensar", "parar", "esperar", "sentar", "levantar",
    ],

    # ADJETIVOS (Azul #2196F3) — Como é
    "adjective": [
        "bom", "mau", "grande", "pequeno", "bonito",
        "mais", "muito", "pouco", "quente", "frio",
        "feliz", "triste", "novo", "velho", "rápido",
        "diferente", "igual", "cheio", "vazio", "certo",
    ],

    # SUBSTANTIVOS (Laranja #FF9800) — O quê
    "noun": [
        "água", "comida", "casa", "escola", "banheiro",
        "mamãe", "papai", "família", "amigo", "professor",
        "dia", "noite", "livro", "bola", "música",
        "carro", "roupa", "sapato", "cama", "mesa",
        "telefone", "televisão", "jogo", "animal", "cachorro",
        "gato", "pão", "leite", "suco", "fruta",
    ],

    # FRASES SOCIAIS (Rosa #E91E63) — Interação
    "social_phrase": [
        "oi", "tchau", "por favor", "obrigado", "desculpa",
        "sim", "não", "bom dia", "boa noite", "tudo bem",
        "de nada", "parabéns",
    ],

    # PERGUNTAS (Ciano #00BCD4) — Perguntar
    "question": [
        "o quê", "quem", "onde", "quando", "por quê",
        "como", "quanto", "qual",
    ],
}

# Layout da prancha Core 4x5 (página principal)
# Organizada para motor planning consistente
CORE_BOARD_4x5: list[list[str]] = [
    # Row 0: Pronomes + Social essencial
    ["eu", "você", "querer", "mais", "sim"],
    # Row 1: Verbos de alta frequência
    ["ir", "gostar", "comer", "beber", "não"],
    # Row 2: Verbos + Adjetivos
    ["fazer", "ajudar", "bom", "grande", "por favor"],
    # Row 3: Necessidades + Social
    ["banheiro", "água", "parar", "oi", "obrigado"],
]

# Layout expandido 6x8 para tablet
CORE_BOARD_6x8: list[list[str]] = [
    # Row 0: Pronomes
    ["eu", "você", "ele", "ela", "nós", "meu", "isso", "aqui"],
    # Row 1: Verbos essenciais
    ["querer", "ir", "gostar", "comer", "beber", "fazer", "ter", "ser"],
    # Row 2: Mais verbos
    ["poder", "precisar", "ver", "ouvir", "brincar", "ajudar", "dar", "pegar"],
    # Row 3: Adjetivos + Advérbios
    ["bom", "mau", "grande", "pequeno", "mais", "muito", "bonito", "feliz"],
    # Row 4: Substantivos frequentes
    ["água", "comida", "casa", "mamãe", "papai", "amigo", "escola", "banheiro"],
    # Row 5: Social + Perguntas
    ["sim", "não", "oi", "tchau", "por favor", "obrigado", "o quê", "onde"],
]


async def find_or_log_symbol(session, keyword: str) -> Symbol | None:
    """Busca um símbolo pelo keyword. Loga se não encontrar."""
    # Busca exata no label_pt
    result = await session.execute(
        select(Symbol).where(Symbol.label_pt == keyword).limit(1)
    )
    symbol = result.scalar_one_or_none()
    if symbol:
        return symbol

    # Busca nas keywords (array contains)
    from sqlalchemy import cast, text
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy import String

    result = await session.execute(
        select(Symbol).where(
            Symbol.keywords.contains([keyword])
        ).limit(1)
    )
    symbol = result.scalar_one_or_none()
    if symbol:
        return symbol

    print(f"  ⚠ Símbolo não encontrado: '{keyword}'")
    return None


async def create_template_board(
    session,
    name: str,
    layout: list[list[str]],
    board_type: BoardType = BoardType.core,
) -> Board:
    """Cria uma prancha template com o layout especificado."""
    rows = len(layout)
    cols = max(len(row) for row in layout)

    board = Board(
        name=name,
        board_type=board_type,
        grid_rows=rows,
        grid_cols=cols,
        is_template=True,
        profile_id=None,
    )
    session.add(board)
    await session.flush()

    cells_created = 0
    for row_idx, row in enumerate(layout):
        for col_idx, keyword in enumerate(row):
            if not keyword:
                continue

            symbol = await find_or_log_symbol(session, keyword)
            if not symbol:
                continue

            cell = BoardCell(
                board_id=board.id,
                position_row=row_idx,
                position_col=col_idx,
                symbol_id=symbol.id,
                action=CellAction.speak,
                background_color=symbol.fitzgerald_color,
                is_hidden=False,
            )
            session.add(cell)
            cells_created += 1

    await session.flush()
    print(f"  ✓ Prancha '{name}' criada: {rows}x{cols}, {cells_created} células")
    return board


async def create_category_boards(session, parent_board: Board) -> list[Board]:
    """Cria sub-pranchas por categoria (navegáveis a partir da prancha core)."""
    category_boards = []

    for gram_class_name, words in CORE_VOCABULARY.items():
        gram_class = GrammaticalClass(gram_class_name)

        # Buscar símbolos para cada palavra
        symbols_found = []
        for word in words:
            sym = await find_or_log_symbol(session, word)
            if sym:
                symbols_found.append(sym)

        if not symbols_found:
            continue

        # Calcular grid (tentar quadrado)
        n = len(symbols_found)
        cols = min(5, n)
        rows = (n + cols - 1) // cols

        # Nomes amigáveis das categorias
        category_names = {
            "pronoun": "Pessoas",
            "verb": "Ações",
            "adjective": "Como é",
            "noun": "Coisas",
            "social_phrase": "Social",
            "question": "Perguntas",
        }

        board = Board(
            name=category_names.get(gram_class_name, gram_class_name),
            board_type=BoardType.category,
            grid_rows=rows,
            grid_cols=cols,
            is_template=True,
            parent_board_id=parent_board.id,
            profile_id=None,
        )
        session.add(board)
        await session.flush()

        for idx, sym in enumerate(symbols_found):
            row = idx // cols
            col = idx % cols
            cell = BoardCell(
                board_id=board.id,
                position_row=row,
                position_col=col,
                symbol_id=sym.id,
                action=CellAction.speak,
                background_color=sym.fitzgerald_color,
                is_hidden=False,
            )
            session.add(cell)

        await session.flush()
        print(f"  ✓ Sub-prancha '{board.name}': {rows}x{cols}, {len(symbols_found)} símbolos")
        category_boards.append(board)

    return category_boards


async def seed_boards() -> None:
    """Executa o seed de pranchas core vocabulary."""
    print("Criando pranchas Core Vocabulary pt-BR...")
    print()

    async with async_session_factory() as session:
        # Verificar se já existem templates
        result = await session.execute(
            select(Board).where(Board.is_template.is_(True)).limit(1)
        )
        if result.scalar_one_or_none():
            print("Pranchas template já existem. Pulando.")
            await engine.dispose()
            return

        # Prancha Core Compacta (4x5 - para celular)
        print("=== Prancha Core Compacta (Celular) ===")
        core_compact = await create_template_board(
            session, "Core - Compacta", CORE_BOARD_4x5
        )

        # Prancha Core Expandida (6x8 - para tablet)
        print("\n=== Prancha Core Expandida (Tablet) ===")
        core_expanded = await create_template_board(
            session, "Core - Expandida", CORE_BOARD_6x8
        )

        # Sub-pranchas por categoria
        print("\n=== Sub-pranchas por Categoria ===")
        await create_category_boards(session, core_compact)

        await session.commit()
        print("\nSeed de pranchas concluído!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_boards())
