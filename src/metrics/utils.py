from datetime import datetime
from typing import Dict, Any, List

from database.schemas.analytics_request import AnalyticsEventRequest


def enrich_event(event: AnalyticsEventRequest) -> Dict[str, Any]:
    """
    
    Обогащение:
    - received_ts (сервер)
    - viewer_id = client_id (перезаписываем, даже если фронт прислал)

    
    Args:
        event: Валидированное событие от фронтенда
        
    Returns:
        Словарь для сохранения в analytics.events
    """
    return {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "event_ts": event.event_ts,
        "session_id": event.session_id,
        "client_id": event.client_id,
        
        "received_ts": datetime.now(datetime.now().astimezone().tzinfo),
        "viewer_id": event.client_id,
        
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        
        "context": event.context.model_dump(by_alias=True),
        "properties": event.properties.model_dump(by_alias=True, exclude_none=True),
        

    }


def extract_daily_view(event: AnalyticsEventRequest) -> Dict[str, Any] | None:
    """
    Извлекает данные для analytics.daily_item_views из события item_card_open_short.
    
    Просмотр баннера (view) фиксируется только при первом событии
    item_card_open_short за сутки на:
    - конкретный баннер (entity_id)
    - конкретного клиента (viewer_id = client_id)
    
    Ключ уникальности: (banner_id, viewer_id, view_date)
    где view_date = date(event_ts в UTC)
    
    Args:
        event: Валидированное событие
        
    Returns:
        Словарь для upsert в daily_item_views или None если не short-событие
    """
    if event.event_name != "item_card_open_short":
        return None
    
    view_date = event.event_ts.date()
    
    viewer_id = event.client_id
    
    return {
        "banner_id": event.entity_id,
        "viewer_id": viewer_id,
        "view_date": view_date,
        "first_event_ts": event.event_ts,
        
        "city": event.properties.banner_city,
        "district": event.properties.banner_district,
        "construction_type": event.properties.banner_constructionType,
        
        "filters": event.context.filters,
    }


def extract_batch_views(events: List[AnalyticsEventRequest]) -> List[Dict[str, Any]]:
    """
    Извлекает все просмотры из батча событий.
    
    Args:
        events: Список валидированных событий
        
    Returns:
        Список просмотров для upsert в daily_item_views
    """
    views = []
    
    for event in events:
        view = extract_daily_view(event)
        if view:
            views.append(view)
    
    return views


def validate_event_whitelist(event_name: str) -> bool:
    """
    Проверяет, входит ли тип события в белый список.
    
    - item_card_open_short (от фронта)
    - item_card_open_full (от фронта)
    - booking_start (от фронта)
    - booking_complete (пишется BE при создании брони)
    - booking_abandon (пишется BE по таймауту)
    
    Args:
        event_name: Тип события
        
    Returns:
        True если событие разрешено
    """
    ALLOWED_EVENTS = {
        "item_card_open_short",
        "item_card_open_full",
        "booking_start",
        "booking_complete", 
        "booking_abandon", 
    }
    
    return event_name in ALLOWED_EVENTS