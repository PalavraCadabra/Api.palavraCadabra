import uuid
from datetime import datetime

from sqlalchemy import and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog


async def aggregate_usage_data(
    session: AsyncSession,
    profile_id: uuid.UUID,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    """Aggregate usage logs into summary statistics for clinical insights."""
    filters = [UsageLog.profile_id == profile_id]
    if since:
        filters.append(UsageLog.timestamp >= since)
    if until:
        filters.append(UsageLog.timestamp <= until)

    where_clause = and_(*filters)

    # Total events
    result = await session.execute(select(func.count(UsageLog.id)).where(where_clause))
    total_events = result.scalar_one()

    # Symbol selections
    symbol_filters = [*filters, UsageLog.event_type == "symbol_selected"]
    symbol_where = and_(*symbol_filters)

    result = await session.execute(select(func.count(UsageLog.id)).where(symbol_where))
    total_symbols = result.scalar_one()

    # Unique symbols (from event_data->>'symbol_label')
    result = await session.execute(
        select(func.count(func.distinct(UsageLog.event_data["symbol_label"].astext))).where(
            symbol_where
        )
    )
    unique_symbols = result.scalar_one() or 0

    # TTR (type-token ratio)
    ttr = (unique_symbols / total_symbols) if total_symbols > 0 else 0.0

    # Unique sessions
    result = await session.execute(
        select(func.count(func.distinct(UsageLog.session_id))).where(where_clause)
    )
    session_count = result.scalar_one() or 0

    # Message sent events for MLU (avg symbols per message)
    msg_filters = [*filters, UsageLog.event_type == "message_sent"]
    msg_where = and_(*msg_filters)
    result = await session.execute(
        select(func.avg(cast(UsageLog.event_data["symbol_count"].astext, func.integer()))).where(
            msg_where
        )
    )
    avg_message_length = result.scalar_one() or 0.0

    # Communication rate: total symbols / total session minutes
    # Approximate from session durations in event_data
    result = await session.execute(
        select(
            func.sum(cast(UsageLog.event_data["duration_seconds"].astext, func.integer()))
        ).where(and_(*filters, UsageLog.event_type == "session_end"))
    )
    total_duration_sec = result.scalar_one() or 0
    communication_rate = (
        (total_symbols / (total_duration_sec / 60.0)) if total_duration_sec > 0 else 0.0
    )

    # Top symbols
    top_symbols_query = (
        select(
            UsageLog.event_data["symbol_label"].astext.label("label"),
            UsageLog.event_data["grammatical_class"].astext.label("class_"),
            func.count(UsageLog.id).label("count"),
        )
        .where(symbol_where)
        .group_by(
            UsageLog.event_data["symbol_label"].astext,
            UsageLog.event_data["grammatical_class"].astext,
        )
        .order_by(func.count(UsageLog.id).desc())
        .limit(20)
    )
    result = await session.execute(top_symbols_query)
    top_symbols = [
        {"label": row.label, "count": row.count, "class": row.class_} for row in result.all()
    ]

    # Daily usage
    daily_query = (
        select(
            func.date_trunc("day", UsageLog.timestamp).label("date"),
            func.count(UsageLog.id).label("count"),
        )
        .where(symbol_where)
        .group_by(func.date_trunc("day", UsageLog.timestamp))
        .order_by(func.date_trunc("day", UsageLog.timestamp))
    )
    result = await session.execute(daily_query)
    daily_usage = [
        {"date": row.date.isoformat() if row.date else "", "count": row.count}
        for row in result.all()
    ]

    # Grammatical class distribution
    class_query = (
        select(
            UsageLog.event_data["grammatical_class"].astext.label("class_"),
            func.count(UsageLog.id).label("count"),
        )
        .where(symbol_where)
        .group_by(UsageLog.event_data["grammatical_class"].astext)
    )
    result = await session.execute(class_query)
    grammatical_class_distribution = {row.class_: row.count for row in result.all() if row.class_}

    return {
        "total_symbols_selected": total_symbols,
        "unique_symbols_used": unique_symbols,
        "ttr": ttr,
        "avg_message_length": float(avg_message_length),
        "communication_rate": communication_rate,
        "top_symbols": top_symbols,
        "daily_usage": daily_usage,
        "session_count": session_count,
        "grammatical_class_distribution": grammatical_class_distribution,
    }
