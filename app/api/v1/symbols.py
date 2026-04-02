import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import cast, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, array
from sqlalchemy import String

from app.api.deps import CurrentUser, DBSession
from app.models.symbol import Symbol
from app.schemas.symbol import SymbolCreate, SymbolRead, SymbolUpdate

router = APIRouter()


@router.get("/", response_model=list[SymbolRead])
async def list_symbols(
    session: DBSession,
    current_user: CurrentUser,
    category: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Symbol]:
    query = select(Symbol)
    if category:
        query = query.where(Symbol.category == category)
    if search:
        query = query.where(
            or_(
                Symbol.label_pt.ilike(f"%{search}%"),
                Symbol.keywords.contains(cast(array([search]), ARRAY(String))),
            )
        )
    query = query.order_by(Symbol.frequency_rank.asc().nullslast()).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{symbol_id}", response_model=SymbolRead)
async def get_symbol(
    symbol_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> Symbol:
    result = await session.execute(select(Symbol).where(Symbol.id == symbol_id))
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return symbol


@router.post("/", response_model=SymbolRead, status_code=status.HTTP_201_CREATED)
async def create_symbol(
    data: SymbolCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> Symbol:
    symbol = Symbol(**data.model_dump())
    session.add(symbol)
    await session.flush()
    await session.refresh(symbol)
    return symbol


@router.patch("/{symbol_id}", response_model=SymbolRead)
async def update_symbol(
    symbol_id: uuid.UUID,
    data: SymbolUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> Symbol:
    result = await session.execute(select(Symbol).where(Symbol.id == symbol_id))
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(symbol, field, value)
    await session.flush()
    await session.refresh(symbol)
    return symbol
