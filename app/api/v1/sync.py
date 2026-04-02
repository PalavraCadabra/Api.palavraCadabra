"""Sync endpoints — LWW (Last-Write-Wins) CRDT sync for offline-first clients."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.models.board import Board
from app.models.board_cell import BoardCell
from app.schemas.sync import (
    SyncBoardData,
    SyncCellData,
    SyncProfileData,
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
)

router = APIRouter()


async def _upsert_profile(
    session: DBSession,
    current_user_id: uuid.UUID,
    data: SyncProfileData,
    device_id: str,
) -> None:
    """Upsert an AACProfile from sync data."""
    result = await session.execute(
        select(AACProfile).where(
            AACProfile.id == data.id,
            AACProfile.user_id == current_user_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.name = data.name
        existing.communication_level = data.communication_level
        existing.motor_capability = data.motor_capability
        existing.visual_capability = data.visual_capability
        existing.preferred_voice = data.preferred_voice
        existing.grid_size_preference = data.grid_size_preference or "4x5"
        existing.updated_at = data.updated_at
        existing.version = data.version
        existing.device_id = device_id
        existing.is_deleted = data.is_deleted
    else:
        profile = AACProfile(
            id=data.id,
            user_id=current_user_id,
            name=data.name,
            communication_level=data.communication_level,
            motor_capability=data.motor_capability,
            visual_capability=data.visual_capability,
            preferred_voice=data.preferred_voice,
            grid_size_preference=data.grid_size_preference or "4x5",
            updated_at=data.updated_at,
            version=data.version,
            device_id=device_id,
            is_deleted=data.is_deleted,
        )
        session.add(profile)


async def _upsert_board(
    session: DBSession,
    data: SyncBoardData,
    device_id: str,
) -> None:
    """Upsert a Board from sync data."""
    result = await session.execute(select(Board).where(Board.id == data.id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.profile_id = data.profile_id
        existing.name = data.name
        existing.board_type = data.board_type
        existing.grid_rows = data.grid_rows
        existing.grid_cols = data.grid_cols
        existing.is_template = data.is_template
        existing.parent_board_id = data.parent_board_id
        existing.updated_at = data.updated_at
        existing.version = data.version
        existing.device_id = device_id
        existing.is_deleted = data.is_deleted
    else:
        board = Board(
            id=data.id,
            profile_id=data.profile_id,
            name=data.name,
            board_type=data.board_type,
            grid_rows=data.grid_rows,
            grid_cols=data.grid_cols,
            is_template=data.is_template,
            parent_board_id=data.parent_board_id,
            updated_at=data.updated_at,
            version=data.version,
            device_id=device_id,
            is_deleted=data.is_deleted,
        )
        session.add(board)


async def _upsert_cell(
    session: DBSession,
    data: SyncCellData,
    device_id: str,
) -> None:
    """Upsert a BoardCell from sync data."""
    result = await session.execute(select(BoardCell).where(BoardCell.id == data.id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.board_id = data.board_id
        existing.position_row = data.position_row
        existing.position_col = data.position_col
        existing.symbol_id = data.symbol_id
        existing.label_override = data.label_override
        existing.action = data.action
        existing.action_target = data.action_target
        existing.background_color = data.background_color
        existing.is_hidden = data.is_hidden
        existing.updated_at = data.updated_at
        existing.version = data.version
        existing.device_id = device_id
        existing.is_deleted = data.is_deleted
    else:
        cell = BoardCell(
            id=data.id,
            board_id=data.board_id,
            position_row=data.position_row,
            position_col=data.position_col,
            symbol_id=data.symbol_id,
            label_override=data.label_override,
            action=data.action,
            action_target=data.action_target,
            background_color=data.background_color,
            is_hidden=data.is_hidden,
            updated_at=data.updated_at,
            version=data.version,
            device_id=device_id,
            is_deleted=data.is_deleted,
        )
        session.add(cell)


@router.post("/push", status_code=status.HTTP_200_OK)
async def sync_push(
    data: SyncPushRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """
    Client pushes local changes to server.
    Uses LWW: if client's updated_at > server's updated_at, client wins.
    Returns conflicts (server items that are newer than what client sent).
    """
    results: dict[str, list] = {"accepted": [], "conflicts": [], "errors": []}

    # Process profiles
    for profile_data in data.profiles:
        try:
            result = await session.execute(
                select(AACProfile).where(
                    AACProfile.id == profile_data.id,
                    AACProfile.user_id == current_user.id,
                )
            )
            existing = result.scalar_one_or_none()

            if not existing or profile_data.updated_at > existing.updated_at:
                await _upsert_profile(session, current_user.id, profile_data, data.device_id)
                results["accepted"].append({"type": "profile", "id": str(profile_data.id)})
            else:
                results["conflicts"].append({
                    "type": "profile",
                    "id": str(profile_data.id),
                    "server_version": existing.version,
                    "server_updated_at": existing.updated_at.isoformat(),
                })
        except Exception as exc:
            results["errors"].append({
                "type": "profile",
                "id": str(profile_data.id),
                "error": str(exc),
            })

    # Process boards
    for board_data in data.boards:
        try:
            result = await session.execute(
                select(Board).where(Board.id == board_data.id)
            )
            existing = result.scalar_one_or_none()

            if not existing or board_data.updated_at > existing.updated_at:
                await _upsert_board(session, board_data, data.device_id)
                results["accepted"].append({"type": "board", "id": str(board_data.id)})
            else:
                results["conflicts"].append({
                    "type": "board",
                    "id": str(board_data.id),
                    "server_version": existing.version,
                    "server_updated_at": existing.updated_at.isoformat(),
                })
        except Exception as exc:
            results["errors"].append({
                "type": "board",
                "id": str(board_data.id),
                "error": str(exc),
            })

    # Process cells
    for cell_data in data.cells:
        try:
            result = await session.execute(
                select(BoardCell).where(BoardCell.id == cell_data.id)
            )
            existing = result.scalar_one_or_none()

            if not existing or cell_data.updated_at > existing.updated_at:
                await _upsert_cell(session, cell_data, data.device_id)
                results["accepted"].append({"type": "cell", "id": str(cell_data.id)})
            else:
                results["conflicts"].append({
                    "type": "cell",
                    "id": str(cell_data.id),
                    "server_version": existing.version,
                    "server_updated_at": existing.updated_at.isoformat(),
                })
        except Exception as exc:
            results["errors"].append({
                "type": "cell",
                "id": str(cell_data.id),
                "error": str(exc),
            })

    await session.commit()
    return results


@router.post("/pull", response_model=SyncPullResponse)
async def sync_pull(
    data: SyncPullRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> SyncPullResponse:
    """
    Client requests all changes since a given timestamp.
    Returns all entities modified after `since` for the user's profiles.
    """
    since = data.since or datetime(2000, 1, 1, tzinfo=timezone.utc)

    # Get all user profiles
    profiles_result = await session.execute(
        select(AACProfile).where(AACProfile.user_id == current_user.id)
    )
    all_profiles = list(profiles_result.scalars().all())
    profile_ids = [p.id for p in all_profiles]

    # Filter modified profiles
    modified_profiles = [p for p in all_profiles if p.updated_at > since]

    # Get modified boards for user's profiles (+ templates)
    if profile_ids:
        boards_result = await session.execute(
            select(Board).where(
                Board.profile_id.in_(profile_ids),
                Board.updated_at > since,
            )
        )
        modified_boards = list(boards_result.scalars().all())
    else:
        modified_boards = []

    # Also include templates modified since
    templates_result = await session.execute(
        select(Board).where(
            Board.is_template.is_(True),
            Board.updated_at > since,
        )
    )
    modified_boards.extend(templates_result.scalars().all())

    # Get modified cells for all modified boards
    board_ids = [b.id for b in modified_boards]
    if board_ids:
        cells_result = await session.execute(
            select(BoardCell).where(
                BoardCell.board_id.in_(board_ids),
                BoardCell.updated_at > since,
            )
        )
        modified_cells = list(cells_result.scalars().all())
    else:
        modified_cells = []

    return SyncPullResponse(
        profiles=[SyncProfileData.model_validate(p) for p in modified_profiles],
        boards=[SyncBoardData.model_validate(b) for b in modified_boards],
        cells=[SyncCellData.model_validate(c) for c in modified_cells],
        server_time=datetime.now(timezone.utc),
    )
