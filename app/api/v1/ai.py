import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.rate_limit import limiter
from app.models.aac_profile import AACProfile
from app.models.board import Board, BoardType
from app.models.board_cell import BoardCell, CellAction
from app.models.symbol import Symbol
from app.schemas.ai import (
    BoardGenerationRequest,
    ClinicalInsightsRequest,
    LanguageExpansionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _ai_unavailable_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI service not configured. Set ANTHROPIC_API_KEY to enable.",
    )


@router.post("/expand-language")
@limiter.limit("10/minute")
async def expand_language(
    request: Request,
    data: LanguageExpansionRequest,
    current_user: CurrentUser,
) -> dict:
    """Expand telegraphic AAC sequence to natural Portuguese."""
    try:
        from app.services.language_expansion import LanguageExpansionService

        service = LanguageExpansionService()
    except RuntimeError:
        raise _ai_unavailable_response()

    try:
        result = await service.expand(data.symbols, data.context)
        return result
    except Exception:
        logger.exception("Language expansion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Language expansion failed",
        )


@router.post("/generate-board")
@limiter.limit("10/minute")
async def generate_board(
    request: Request,
    data: BoardGenerationRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Generate a personalized board using AI."""
    try:
        from app.services.board_generation import BoardGenerationService

        service = BoardGenerationService()
    except RuntimeError:
        raise _ai_unavailable_response()

    # Get profile
    result = await session.execute(
        select(AACProfile).where(AACProfile.id == data.profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Get available symbols
    result = await session.execute(select(Symbol).limit(500))
    available = [
        {"label_pt": s.label_pt, "grammatical_class": s.grammatical_class.value}
        for s in result.scalars()
    ]

    try:
        ai_result = await service.generate_board(
            profile={
                "name": profile.name,
                "communication_level": profile.communication_level.value,
                "motor_capability": profile.motor_capability.value,
            },
            board_type=data.board_type,
            context=data.context,
            available_symbols=available,
        )
    except Exception:
        logger.exception("Board generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Board generation failed",
        )

    # Auto-create board in DB if requested
    if data.auto_create:
        board = Board(
            profile_id=data.profile_id,
            name=ai_result.get("name", "Prancha IA"),
            board_type=BoardType(data.board_type)
            if data.board_type in BoardType.__members__
            else BoardType.personal,
            grid_rows=ai_result.get("grid_rows", 4),
            grid_cols=ai_result.get("grid_cols", 5),
            is_template=False,
        )
        session.add(board)
        await session.flush()

        for cell_data in ai_result.get("cells", []):
            # Try to match generated label to an actual symbol
            symbol = await _find_symbol_by_label(session, cell_data.get("label", ""))
            cell = BoardCell(
                board_id=board.id,
                position_row=cell_data.get("row", 0),
                position_col=cell_data.get("col", 0),
                symbol_id=symbol.id if symbol else None,
                label_override=cell_data.get("label") if not symbol else None,
                action=CellAction.speak,
                background_color=_fitzgerald_color(
                    cell_data.get("grammatical_class", "misc")
                ),
            )
            session.add(cell)

        await session.commit()
        ai_result["board_id"] = str(board.id)

    return ai_result


@router.post("/clinical-insights")
@limiter.limit("10/minute")
async def clinical_insights(
    request: Request,
    data: ClinicalInsightsRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Generate clinical insights for a patient."""
    try:
        from app.services.clinical_insights import ClinicalInsightsService

        service = ClinicalInsightsService()
    except RuntimeError:
        raise _ai_unavailable_response()

    # Get profile
    result = await session.execute(
        select(AACProfile).where(AACProfile.id == data.profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Aggregate usage data
    from app.services.usage_analytics import aggregate_usage_data

    usage_summary = await aggregate_usage_data(
        session, data.profile_id, data.since, data.until
    )

    try:
        result = await service.generate_insights(
            profile={
                "name": profile.name,
                "communication_level": profile.communication_level.value,
                "motor_capability": profile.motor_capability.value,
            },
            usage_summary=usage_summary,
            recent_sessions=[],
        )
        return result
    except Exception:
        logger.exception("Clinical insights generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clinical insights generation failed",
        )


async def _find_symbol_by_label(
    session: DBSession, label: str
) -> Symbol | None:
    """Find a symbol by its Portuguese label (case-insensitive)."""
    if not label:
        return None
    result = await session.execute(
        select(Symbol).where(Symbol.label_pt.ilike(label)).limit(1)
    )
    return result.scalar_one_or_none()


def _fitzgerald_color(grammatical_class: str) -> str:
    """Return Fitzgerald Key color for a grammatical class."""
    colors = {
        "pronoun": "#FFD700",  # yellow
        "verb": "#4CAF50",  # green
        "adjective": "#2196F3",  # blue
        "noun": "#FF9800",  # orange
        "social_phrase": "#E91E63",  # pink
        "question": "#00BCD4",  # cyan
        "misc": "#9E9E9E",  # gray
    }
    return colors.get(grammatical_class, "#FFFFFF")
