from datetime import date, datetime
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    Date,
    Index,
    PrimaryKeyConstraint,
    text,
    Computed,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_model import Base


class AnalyticsEvent(Base):
    """
    """
    __table_args__ = (
        Index("ix_events_name_ts", "event_name", "event_ts"),
        Index("ix_events_entity", "entity_type", "entity_id", "event_ts"),
        Index("ix_events_client_ts", "client_id", "event_ts"),
        Index("ix_events_session_ts", "session_id", "event_ts"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True,
        comment="UUID события от фронтенда"
    )
    event_name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        comment="Тип события (item_card_open_short, booking_start, etc.)"
    )
    event_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Временная метка от клиента (UTC)"
    )
    received_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Время получения сервером (добавляется BE)"
    )
    
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=False,
        comment="ID сессии (вкладка браузера)"
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=False,
        comment="ID клиента из localStorage"
    )
    viewer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=False,
        comment="ID зрителя (добавляется BE: viewer_id = client_id)"
    )
    
    entity_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Тип сущности (banner)"
    )
    entity_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False,
        comment="ID баннера"
    )
    
    context: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'{}'::jsonb"),
        comment="Контекст события (page, city, district, filters)"
    )
    properties: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'{}'::jsonb"),
        comment="Свойства события (source, card_level, banner_city, etc.)"
    )
    
    city: Mapped[str | None] = mapped_column(
        String(100),
        Computed("(context->>'city')"),
        comment="Извлечено из context.city"
    )
    district: Mapped[str | None] = mapped_column(
        String(100),
        Computed("(properties->>'banner_district')"),
        comment="Извлечено из properties.banner_district"
    )
    construction_type: Mapped[str | None] = mapped_column(
        String(50),
        Computed("(properties->>'banner_constructionType')"),
        comment="Извлечено из properties.banner_constructionType"
    )


class DailyItemView(Base):
    """
    Таблица уникальных дневных просмотров баннеров (дедупликация).
    
    Правило из ТЗ (раздел 8):
    Просмотр баннера (view) фиксируется только при первом событии
    item_card_open_short за сутки на:
    - конкретный баннер
    - конкретного клиента
    
    Ключ уникальности: (banner_id, viewer_id, view_date)
    где view_date = date(event_ts в UTC)
    """
    __table_args__ = (
        PrimaryKeyConstraint("banner_id", "viewer_id", "view_date"),
        Index("ix_daily_views_date", "view_date"),
        Index("ix_daily_views_banner", "banner_id", "view_date"),
        Index("ix_daily_views_city_district", "city", "district", "view_date"),
    )

    banner_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False,
        comment="ID баннера"
    )
    viewer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=False,
        comment="ID зрителя (= client_id)"
    )
    view_date: Mapped[date] = mapped_column(
        Date, 
        nullable=False,
        comment="Дата просмотра (UTC date)"
    )
    
    first_event_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Timestamp первого просмотра в эту дату"
    )
    
    city: Mapped[str | None] = mapped_column(
        String(100),
        comment="properties.banner_city"
    )
    district: Mapped[str | None] = mapped_column(
        String(100),
        comment="properties.banner_district"
    )
    construction_type: Mapped[str | None] = mapped_column(
        String(50),
        comment="properties.banner_constructionType"
    )
    
    filters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'{}'::jsonb"),
        comment="Активные фильтры из context.filters"
    )


class EventReject(Base):
    """
    
    Сохраняет события, которые не прошли валидацию.
    """
    __table_args__ = (
        Index("ix_rejects_ts", "reject_ts"),
        Index("ix_rejects_event_name", "event_name"),
    )

    reject_id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True
    )
    reject_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Время отклонения"
    )
    
    event_name: Mapped[str | None] = mapped_column(
        String(100),
        comment="Тип события (если удалось извлечь)"
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Причина отклонения"
    )
    
    raw_event: Mapped[Dict[str, Any] | None] = mapped_column(
        JSONB,
        comment="Сырой JSON события"
    )
    
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        comment="ID клиента (если удалось извлечь)"
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        comment="ID сессии (если удалось извлечь)"
    )