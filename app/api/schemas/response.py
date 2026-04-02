from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Citation(BaseModel):
    doc_id: str
    title: str
    snippet: str
    uri: Optional[str] = None


class TraceInfo(BaseModel):
    request_id: str
    latency_ms: int


class QueryResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    trace: TraceInfo
