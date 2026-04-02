import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.board import Board
from app.models.board_cell import BoardCell
from app.schemas.board import (
    BoardCellCreate,
    BoardCellRead,
    BoardCellUpdate,
    BoardCreate,
    BoardRead,
    BoardUpdate,
)

router = APIRouter()


@router.post("/", response_model=BoardRead, status_code=status.HTTP_201_CREATED)
async def create_board(
    data: BoardCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> Board:
    board_data = data.model_dump(exclude={"cells"})
    board = Board(**board_data)
    session.add(board)
    await session.flush()

    for cell_data in data.cells:
        cell = BoardCell(board_id=board.id, **cell_data.model_dump())
        session.add(cell)

    await session.flush()
    await session.refresh(board)
    return board


@router.get("/", response_model=list[BoardRead])
async def list_boards(
    session: DBSession,
    current_user: CurrentUser,
    profile_id: uuid.UUID | None = None,
    templates_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Board]:
    query = select(Board)
    if templates_only:
        query = query.where(Board.is_template.is_(True))
    elif profile_id:
        query = query.where(Board.profile_id == profile_id)
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{board_id}", response_model=BoardRead)
async def get_board(
    board_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> Board:
    result = await session.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


@router.patch("/{board_id}", response_model=BoardRead)
async def update_board(
    board_id: uuid.UUID,
    data: BoardUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> Board:
    result = await session.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(board, field, value)
    await session.flush()
    await session.refresh(board)
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> None:
    result = await session.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    await session.delete(board)
    await session.commit()


# --- Cell endpoints ---


@router.post("/{board_id}/cells", response_model=BoardCellRead, status_code=status.HTTP_201_CREATED)
async def add_cell(
    board_id: uuid.UUID,
    data: BoardCellCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> BoardCell:
    result = await session.execute(select(Board).where(Board.id == board_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")

    cell = BoardCell(board_id=board_id, **data.model_dump())
    session.add(cell)
    await session.flush()
    await session.refresh(cell)
    return cell


@router.patch("/{board_id}/cells/{cell_id}", response_model=BoardCellRead)
async def update_cell(
    board_id: uuid.UUID,
    cell_id: uuid.UUID,
    data: BoardCellUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> BoardCell:
    result = await session.execute(
        select(BoardCell).where(BoardCell.id == cell_id, BoardCell.board_id == board_id)
    )
    cell = result.scalar_one_or_none()
    if not cell:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cell not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cell, field, value)
    await session.flush()
    await session.refresh(cell)
    return cell


@router.delete("/{board_id}/cells/{cell_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cell(
    board_id: uuid.UUID,
    cell_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> None:
    result = await session.execute(
        select(BoardCell).where(BoardCell.id == cell_id, BoardCell.board_id == board_id)
    )
    cell = result.scalar_one_or_none()
    if not cell:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cell not found")
    await session.delete(cell)
    await session.commit()
