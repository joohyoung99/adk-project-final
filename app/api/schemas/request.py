from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="사용자 질의", min_length=1)
    session_id: Optional[str] = Field(None, description="세션 ID")
    top_k: int = Field(5, ge=1, le=20, description="검색 결과 수")
    filters: Optional[Dict[str, Any]] = Field(None, description="검색 필터")
