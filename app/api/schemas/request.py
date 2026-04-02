from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="사용자 질의", min_length=1)
    session_id: Optional[str] = Field(None, description="세션 ID (대화 유지용)")
    user_id: Optional[str] = Field(None, description="사용자 ID (세션 격리용)")
