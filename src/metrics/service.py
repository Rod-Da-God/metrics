import logging
from typing import List, Tuple

from database.repository.analytics_repository import AnalyticsRepository
from database.schemas.analytics_request import (
    AnalyticsEventRequest,
    EventsBatchRequest
)
from metrics.utils import (
    enrich_event,
    extract_batch_views,
    validate_event_whitelist
)


logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Сервис оркестрации аналитических событий.
    
    Отвечает за:
    1. Валидацию событий (whitelist)
    2. Обогащение событий серверными данными
    3. Сохранение в analytics.events
    4. Дедупликацию просмотров в analytics.daily_item_views
    5. Логирование отклоненных событий
    """
    
    @staticmethod
    async def process_events_batch(batch: EventsBatchRequest) -> Tuple[int, int]:
        """
        Обрабатывает батч событий от фронтенда.
        
        Поток:
        1. Валидация каждого события (whitelist)
        2. Обогащение валидных событий
        3. Сохранение всех событий в analytics.events
        4. Извлечение просмотров (item_card_open_short)
        5. Upsert просмотров в analytics.daily_item_views (дедупликация)
        6. Логирование отклоненных событий
        
        Args:
            batch: Батч событий от фронтенда (до 200 шт)
            
        Returns:
            Кортеж (accepted_count, rejected_count)
        """
        valid_events: List[AnalyticsEventRequest] = []
        rejected_events: List[Tuple[AnalyticsEventRequest, str]] = []
        
        for event in batch.events:
            if validate_event_whitelist(event.event_name):
                valid_events.append(event)
            else:
                reason = f"event_name '{event.event_name}' не в whitelist"
                rejected_events.append((event, reason))
                logger.warning(
                    "Событие отклонено: event_id=%s, reason=%s",
                    event.event_id,
                    reason
                )
        
        if not valid_events:
            logger.warning("Все события в батче отклонены")
            await AnalyticsService._log_rejected_events(rejected_events)
            return 0, len(rejected_events)
        
        enriched_events = [enrich_event(event) for event in valid_events]
        
        saved_count = await AnalyticsRepository.save_events(enriched_events)
        
        views = extract_batch_views(valid_events)
        
        if views:
            new_views = await AnalyticsRepository.upsert_daily_views(views)
            logger.info(
                "Обработано просмотров: %d переданных, %d новых (остальные дубли)",
                len(views),
                new_views
            )
        
        if rejected_events:
            await AnalyticsService._log_rejected_events(rejected_events)
        
        logger.info(
            "Батч обработан: %d принято, %d отклонено",
            saved_count,
            len(rejected_events)
        )
        
        return saved_count, len(rejected_events)
    
    @staticmethod
    async def _log_rejected_events(
        rejected: List[Tuple[AnalyticsEventRequest, str]]
    ) -> None:
        """
        Логирует отклоненные события в analytics.event_rejects.
        
        Args:
            rejected: Список кортежей (событие, причина отклонения)
        """
        for event, reason in rejected:
            try:
                await AnalyticsRepository.save_rejected_event(
                    event_name=event.event_name,
                    reason=reason,
                    raw_event=event.model_dump(mode="json"),
                    client_id=event.client_id,
                    session_id=event.session_id
                )
            except Exception as e:
                logger.error(
                    "Не удалось сохранить rejected event: event_id=%s, error=%s",
                    event.event_id,
                    e
                )
    
    @staticmethod
    async def check_health() -> bool:
        """
        Проверяет health приложения (доступность БД).
        
        Returns:
            True если все ок
        """
        return await AnalyticsRepository.check_database_health()