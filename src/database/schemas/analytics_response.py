from pydantic import BaseModel, Field


class EventsBatchResponse(BaseModel):
    """Ответ на POST /analytics/events."""
    
    accepted: int = Field(..., description="Количество принятых событий")
    rejected: int = Field(default=0, description="Количество отклоненных событий")
    message: str = Field(default="Events processed successfully")
    
    class Config:
        json_schema_extra = {
            "example": {
                "accepted": 3,
                "rejected": 0,
                "message": "Events processed successfully"
            }
        }


class HealthCheckResponse(BaseModel):
    """Ответ health check эндпоинта."""
    
    status: str = Field(default="ok")
    database: str = Field(default="connected")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "database": "connected"
            }
        }