import logging
from typing import List, Dict, Any
from uuid import UUID
from supabase import create_client, Client
from datetime import datetime, date
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class AnalyticsRepository:
    """
    Репозиторий для работы с аналитическими событиями.
    
    Отвечает за:
    - Сохранение сырых событий в analytics.events
    - Дедупликацию просмотров в analytics.daily_item_views (upsert)
    - Логирование отклоненных событий в analytics.event_rejects
    """
    
    @classmethod
    async def save_events(
        cls, 
        events: List[Dict[str, Any]]
    ) -> int:
        """
        Сохранить батч событий в analytics.events.
        
        Args:
            events: Список событий (уже обогащенных received_ts, viewer_id)
            
        Returns:
            Количество сохраненных событий
        """
        if not events:
            return 0
        
        # Преобразуем UUID в строки для каждого события
        processed_events = []
        for event in events:
            # Создаем копию события и преобразуем все UUID
            processed_event = convert_uuid_to_str(event)
            
            # Преобразуем datetime в строку ISO формата
            if isinstance(processed_event.get('event_ts'), datetime):
                processed_event['event_ts'] = processed_event['event_ts'].isoformat()
            if isinstance(processed_event.get('received_ts'), datetime):
                processed_event['received_ts'] = processed_event['received_ts'].isoformat()
            
            processed_events.append(processed_event)

        response = supabase.table("analytics_events").insert(processed_events).execute()

        logger.debug(f"Response: {response}")

        if hasattr(response, 'data'):
            inserted = len(response.data)
            logger.info("Inserted %d events", inserted)
        else:
            logger.error("Insert failed, error: %r", getattr(response, 'error', None))
            inserted = 0

        return inserted

    @classmethod
    async def upsert_daily_views(
        cls,
        views: List[Dict[str, Any]]
    ) -> int:
        """
        Upsert уникальных дневных просмотров в analytics.daily_item_views.

        Args:
            views: Список просмотров для upsert
            
        Returns:
            Количество НОВЫХ просмотров (inserted)
        """
        if not views:
            return 0
        
        processed_views = []
        for view in views:
            processed_view = convert_uuid_to_str(view)

            if 'view_date' in processed_view and not isinstance(processed_view['view_date'], str):
                if isinstance(processed_view['view_date'], (datetime, date)):
                    processed_view['view_date'] = processed_view['view_date'].isoformat()
            processed_views.append(processed_view)
        
        response = supabase.table("daily_item_views").insert(
            processed_views,
            upsert=True
        ).execute()
        
        if hasattr(response, 'data'):
            inserted = len(response.data)
            logger.info(
                "Обработано %d просмотров: %d новых вставлено",
                len(views),
                inserted
            )
            return inserted
        else:
            logger.error("Ошибка при upsert: %s", getattr(response, 'error', None))
            return 0



    @classmethod
    async def save_rejected_event(
        cls,
        event_name: str | None,
        reason: str,
        raw_event: Dict[str, Any] | None,
        client_id: UUID | None,
        session_id: UUID | None
    ) -> None:
        """
        Сохранить отклоненное событие для мониторинга.
        
        Args:
            event_name: Тип события (если удалось извлечь)
            reason: Причина отклонения
            raw_event: Сырой JSON события
            client_id: ID клиента (если удалось извлечь)
            session_id: ID сессии (если удалось извлечь)
        """
        data = {
            "event_name": event_name,
            "reason": reason,
            "raw_event": raw_event,
            "client_id": convert_uuid_to_str(client_id),
            "session_id": convert_uuid_to_str(session_id)
        }
        
        response = supabase.table("event_rejects").insert(data).execute()
        
        if hasattr(response, 'data') and response.data:
            logger.warning("Событие отклонено: event_name=%s, reason=%s", event_name, reason)
        else:
            logger.error("Ошибка при сохранении отклоненного события: %s", getattr(response, 'error', None))

def convert_uuid_to_str(data: Any) -> Any:
    """Рекурсивно преобразует все UUID и даты в строку в словаре."""
    if isinstance(data, UUID):
        return str(data)
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, dict):
        return {key: convert_uuid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_uuid_to_str(item) for item in data]
    elif hasattr(data, '__str__') and not isinstance(data, (str, int, float, bool, type(None))):
        return str(data)
    return data