import logging
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.core.connection import connection
from database.models.analytics_models import (
    AnalyticsEvent,
    DailyItemView,
    EventReject
)
from database.repository.postgre_repo import PostgreRepository


logger = logging.getLogger(__name__)


class AnalyticsRepository(PostgreRepository[AnalyticsEvent]):
    """
    Репозиторий для работы с аналитическими событиями.
    
    Отвечает за:
    - Сохранение сырых событий в analytics.events
    - Дедупликацию просмотров в analytics.daily_item_views (upsert)
    - Логирование отклоненных событий в analytics.event_rejects
    """
    model = AnalyticsEvent
    
    @classmethod
    @connection()
    async def save_events(
        cls, 
        events: List[Dict[str, Any]], 
        session: AsyncSession
    ) -> int:
        """
        Сохранить батч событий в analytics.events.
        
        Args:
            events: Список событий (уже обогащенных received_ts, viewer_id)
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            Количество сохраненных событий
        """
        if not events:
            return 0
        
        stmt = insert(AnalyticsEvent).values(events)
        
        result = await session.execute(stmt)
        logger.info("Сохранено %d событий в analytics.events", result.rowcount)
        
        return result.rowcount
    
    @classmethod
    @connection()
    async def upsert_daily_views(
        cls,
        views: List[Dict[str, Any]],
        session: AsyncSession
    ) -> int:
        """
        Upsert уникальных дневных просмотров в analytics.daily_item_views.
        
        Логика дедупликации: по ключу (banner_id, viewer_id, view_date)
        при конфликте - игнорируем (оставляем первый просмотр дня).
        
        Args:
            views: Список просмотров для upsert
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            Количество НОВЫХ просмотров (inserted)
        """
        if not views:
            return 0
        
        stmt = pg_insert(DailyItemView).values(views)
        
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["banner_id", "viewer_id", "view_date"]
        )
        
        result = await session.execute(stmt)
        
        inserted = result.rowcount
        logger.info(
            "Upsert %d просмотров в daily_item_views: %d новых, %d дублей пропущено",
            len(views),
            inserted,
            len(views) - inserted
        )
        
        return inserted
    
    @classmethod
    @connection()
    async def save_rejected_event(
        cls,
        event_name: str | None,
        reason: str,
        raw_event: Dict[str, Any] | None,
        client_id: UUID | None,
        session_id: UUID | None,
        session: AsyncSession
    ) -> None:
        """
        Сохранить отклоненное событие для мониторинга.
        
        Args:
            event_name: Тип события (если удалось извлечь)
            reason: Причина отклонения
            raw_event: Сырой JSON события
            client_id: ID клиента (если удалось извлечь)
            session_id: ID сессии (если удалось извлечь)
            session: Асинхронная сессия SQLAlchemy
        """
        stmt = insert(EventReject).values(
            event_name=event_name,
            reason=reason,
            raw_event=raw_event,
            client_id=client_id,
            session_id=session_id
        )
        
        await session.execute(stmt)
        logger.warning(
            "Событие отклонено: event_name=%s, reason=%s", 
            event_name, 
            reason
        )
    
