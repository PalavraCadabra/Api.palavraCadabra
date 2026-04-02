"""Backup and restore endpoints — export/import all user data as JSON."""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.models.board import Board
from app.models.board_cell import BoardCell
from app.schemas.backup import (
    BackupExportResponse,
    BackupImportRequest,
    BackupImportResponse,
    BackupUserData,
)
from app.schemas.sync import SyncBoardData, SyncCellData, SyncProfileData

router = APIRouter()


@router.get("/export", response_model=BackupExportResponse)
async def export_user_data(
    session: DBSession,
    current_user: CurrentUser,
) -> BackupExportResponse:
    """Export all user data as a single JSON blob for backup."""
    # Get all profiles
    profiles_result = await session.execute(
        select(AACProfile).where(AACProfile.user_id == current_user.id)
    )
    profiles = list(profiles_result.scalars().all())
    profile_ids = [p.id for p in profiles]

    # Get all boards for user's profiles
    all_boards: list[Board] = []
    if profile_ids:
        boards_result = await session.execute(
            select(Board).where(Board.profile_id.in_(profile_ids))
        )
        all_boards = list(boards_result.scalars().all())

    # Get all cells for those boards
    board_ids = [b.id for b in all_boards]
    all_cells: list[BoardCell] = []
    if board_ids:
        cells_result = await session.execute(
            select(BoardCell).where(BoardCell.board_id.in_(board_ids))
        )
        all_cells = list(cells_result.scalars().all())

    return BackupExportResponse(
        version="1.0",
        exported_at=datetime.now(timezone.utc).isoformat(),
        user=BackupUserData(
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role.value,
        ),
        profiles=[SyncProfileData.model_validate(p) for p in profiles],
        boards=[SyncBoardData.model_validate(b) for b in all_boards],
        cells=[SyncCellData.model_validate(c) for c in all_cells],
    )


@router.post("/import", response_model=BackupImportResponse, status_code=status.HTTP_200_OK)
async def import_user_data(
    data: BackupImportRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> BackupImportResponse:
    """Import user data from a backup. Merges with existing data using LWW."""
    counts = {"profiles": 0, "boards": 0, "cells": 0}

    # Import profiles
    for profile_data in data.profiles:
        result = await session.execute(
            select(AACProfile).where(
                AACProfile.id == profile_data.id,
                AACProfile.user_id == current_user.id,
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            profile = AACProfile(
                id=profile_data.id,
                user_id=current_user.id,
                name=profile_data.name,
                communication_level=profile_data.communication_level,
                motor_capability=profile_data.motor_capability,
                visual_capability=profile_data.visual_capability,
                preferred_voice=profile_data.preferred_voice,
                grid_size_preference=profile_data.grid_size_preference or "4x5",
                version=profile_data.version,
                device_id=profile_data.device_id,
                is_deleted=profile_data.is_deleted,
            )
            session.add(profile)
            counts["profiles"] += 1
        elif profile_data.updated_at > existing.updated_at:
            existing.name = profile_data.name
            existing.communication_level = profile_data.communication_level
            existing.motor_capability = profile_data.motor_capability
            existing.visual_capability = profile_data.visual_capability
            existing.preferred_voice = profile_data.preferred_voice
            existing.grid_size_preference = profile_data.grid_size_preference or "4x5"
            existing.version = profile_data.version
            existing.device_id = profile_data.device_id
            existing.is_deleted = profile_data.is_deleted
            counts["profiles"] += 1

    # Import boards
    for board_data in data.boards:
        result = await session.execute(
            select(Board).where(Board.id == board_data.id)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            board = Board(
                id=board_data.id,
                profile_id=board_data.profile_id,
                name=board_data.name,
                board_type=board_data.board_type,
                grid_rows=board_data.grid_rows,
                grid_cols=board_data.grid_cols,
                is_template=board_data.is_template,
                parent_board_id=board_data.parent_board_id,
                version=board_data.version,
                device_id=board_data.device_id,
                is_deleted=board_data.is_deleted,
            )
            session.add(board)
            counts["boards"] += 1
        elif board_data.updated_at > existing.updated_at:
            existing.profile_id = board_data.profile_id
            existing.name = board_data.name
            existing.board_type = board_data.board_type
            existing.grid_rows = board_data.grid_rows
            existing.grid_cols = board_data.grid_cols
            existing.is_template = board_data.is_template
            existing.parent_board_id = board_data.parent_board_id
            existing.version = board_data.version
            existing.device_id = board_data.device_id
            existing.is_deleted = board_data.is_deleted
            counts["boards"] += 1

    # Import cells
    for cell_data in data.cells:
        result = await session.execute(
            select(BoardCell).where(BoardCell.id == cell_data.id)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            cell = BoardCell(
                id=cell_data.id,
                board_id=cell_data.board_id,
                position_row=cell_data.position_row,
                position_col=cell_data.position_col,
                symbol_id=cell_data.symbol_id,
                label_override=cell_data.label_override,
                action=cell_data.action,
                action_target=cell_data.action_target,
                background_color=cell_data.background_color,
                is_hidden=cell_data.is_hidden,
                version=cell_data.version,
                device_id=cell_data.device_id,
                is_deleted=cell_data.is_deleted,
            )
            session.add(cell)
            counts["cells"] += 1
        elif cell_data.updated_at > existing.updated_at:
            existing.board_id = cell_data.board_id
            existing.position_row = cell_data.position_row
            existing.position_col = cell_data.position_col
            existing.symbol_id = cell_data.symbol_id
            existing.label_override = cell_data.label_override
            existing.action = cell_data.action
            existing.action_target = cell_data.action_target
            existing.background_color = cell_data.background_color
            existing.is_hidden = cell_data.is_hidden
            existing.version = cell_data.version
            existing.device_id = cell_data.device_id
            existing.is_deleted = cell_data.is_deleted
            counts["cells"] += 1

    await session.commit()

    return BackupImportResponse(
        imported=counts,
        server_time=datetime.now(timezone.utc),
    )
