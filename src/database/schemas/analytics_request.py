from datetime import datetime
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventContext(BaseModel):
    """
    Контекст события (устойчивые параметры страницы).
    
    Принимаем ровно то, что шлет фронт (без изменений).
    """
    
    page: str = Field(..., description="Страница (map, booking)")
    city: str | None = Field(None, description="Код города (khabarovsk)")
    district: str | None = Field(None, description="Район (может быть null)")
    constructionType: str | None = Field(None, description="Тип конструкции (может быть null)")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Активные фильтры (принимаем как есть - структура варьируется)"
    )
    
    class Config:
        populate_by_name = True


class EventProperties(BaseModel):
    """
    Свойства события (специфичные для типа события).
    
    Принимаем ВСЕ поля от фронта (не фильтруем).
    Валидацию делаем минимальную - фронт может присылать разные поля.
    """
    
    # Общие поля
    source: str | None = Field(None, description="Источник (marker_click, short_card_button)")
    card_level: str | None = Field(None, description="Уровень карточки (short, full)")
    
    banner_city: str | None = Field(None, description="Город баннера")
    banner_district: str | None = Field(None, description="Район баннера")
    banner_constructionType: str | None = Field(None, description="Тип конструкции")
    banner_address: str | None = Field(None, description="Адрес баннера")
    
    side_id: str | None = Field(None, description="ID стороны")
    side_key: str | None = Field(None, description="Ключ стороны (A, B)")
    side_keys: List[str] | None = Field(None, description="Список ключей сторон")
    
    step: str | None = Field(None, description="Шаг бронирования (start)")
    months: List[str] | None = Field(None, description="Выбранные месяцы")
    selected_services: List[str] | None = Field(None, description="Выбранные услуги")
    price: Dict[str, Any] | None = Field(None, description="Детали цены")
    
    class Config:
        populate_by_name = True
        extra = "allow"


class AnalyticsEventRequest(BaseModel):
    """
    Схема одного события от фронтенда.
    
    Принимаем РОВНО то, что шлет фронт (примеры из чата Ksu).
    """
    
    event_id: UUID = Field(..., description="UUID события (генерируется на фронте)")
    event_name: str = Field(..., description="Тип события")  # Убрал Literal - whitelist проверяем в service
    event_ts: datetime = Field(..., description="Timestamp от клиента (ISO-8601 UTC)")
    
    client_id: UUID = Field(..., description="UUID клиента из localStorage")
    session_id: UUID = Field(..., description="UUID сессии (вкладка браузера)")
    viewer_id: UUID = Field(..., description="ID зрителя (= client_id на фронте, BE перезапишет)")
    
    entity_type: str = Field(..., description="Тип сущности")
    entity_id: int = Field(..., ge=1, description="ID баннера")
    
    context: EventContext = Field(..., description="Контекст события")
    properties: EventProperties = Field(..., description="Свойства события")
    
    @field_validator("event_ts")
    @classmethod
    def validate_event_ts(cls, v: datetime) -> datetime:
        """Проверяем, что event_ts не из будущего более чем на 1 час (защита от некорректных часов)."""
        now = datetime.now(v.tzinfo)
        if v > now:
            diff_seconds = (v - now).total_seconds()
            if diff_seconds > 3600:
                raise ValueError(f"event_ts слишком далеко в будущем: {diff_seconds}s")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "88c6d5b4-3214-4248-aa6c-5e66012bf073",
                "event_name": "item_card_open_short",
                "event_ts": "2025-12-03T04:03:03.508Z",
                "client_id": "800255f0-e1b4-46b8-b1c2-aa325437a99c",
                "session_id": "951c0b32-126f-4a4b-9554-d1093ff146fe",
                "viewer_id": "800255f0-e1b4-46b8-b1c2-aa325437a99c",
                "entity_type": "banner",
                "entity_id": 144,
                "context": {
                    "page": "map",
                    "city": "khabarovsk",
                    "district": None,
                    "constructionType": None,
                    "filters": {
                        "district": None,
                        "constructionType": None,
                        "status": "Свободно",
                        "month": "2025-12",
                        "priceRange": [10000, 70000]
                    }
                },
                "properties": {
                    "source": "marker_click",
                    "card_level": "short",
                    "banner_city": "Хабаровск",
                    "banner_district": "Центральный",
                    "banner_constructionType": "3,7x2,7",
                    "banner_address": "ул. Ленина, 32",
                    "side_keys": ["A", "B"]
                }
            }
        }


class EventsBatchRequest(BaseModel):
    """
    Схема батча событий (до 200 событий за раз).
    
    Соответствует endpoint POST /analytics/events из ТЗ (раздел 10.1).
    """
    
    events: List[AnalyticsEventRequest] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Батч событий (1-200 шт)"
    )
    
    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v: List[AnalyticsEventRequest]) -> List[AnalyticsEventRequest]:
        """Проверяем размер батча."""
        if len(v) > 200:
            raise ValueError("Батч не может содержать более 200 событий")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_id": "88c6d5b4-3214-4248-aa6c-5e66012bf073",
                        "event_name": "item_card_open_short",
                        "event_ts": "2025-12-03T04:03:03.508Z",
                        "client_id": "800255f0-e1b4-46b8-b1c2-aa325437a99c",
                        "session_id": "951c0b32-126f-4a4b-9554-d1093ff146fe",
                        "viewer_id": "800255f0-e1b4-46b8-b1c2-aa325437a99c",
                        "entity_type": "banner",
                        "entity_id": 144,
                        "context": {
                            "page": "map",
                            "city": "khabarovsk",
                            "filters": {
                                "status": "Свободно"
                            }
                        },
                        "properties": {
                            "source": "marker_click",
                            "banner_city": "Хабаровск",
                            "banner_district": "Центральный"
                        }
                    }
                ]
            }
        }