import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from database.schemas.analytics_request import EventsBatchRequest
from database.schemas.analytics_response import (
    EventsBatchResponse,
    
)
from metrics.service import AnalyticsService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/events",
    response_model=EventsBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Прием батча аналитических событий",
    description="""
    
    Поток обработки:
    1. Валидация структуры
    2. Проверка whitelist event_name
    3. Обогащение серверными данными (received_ts, viewer_id)
    4. Сохранение в analytics.events
    5. Дедупликация просмотров в analytics.daily_item_views
    6. Логирование отклоненных событий в analytics.event_rejects
    
    Ограничения:
    - Батч: 1-200 событий
    - Размер запроса: до 2 МБ
    - event_name должен быть в whitelist
    """,
)
async def receive_events(batch: EventsBatchRequest) -> EventsBatchResponse:
    """
    Endpoint для приема аналитических событий.
    
    Args:
        batch: Батч событий от фронтенда
        
    Returns:
        Статистика обработки (accepted/rejected)
        
    Raises:
        HTTPException 400: Невалидные данные
        HTTPException 500: Ошибка сохранения в БД
    """
    try:
        accepted, rejected = await AnalyticsService.process_events_batch(batch)
        
        return EventsBatchResponse(
            accepted=accepted,
            rejected=rejected,
            message="Events processed successfully"
        )
        
    except ValidationError as e:
        logger.error("Валидация батча провалена: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
        


