import uuid
import time
import os
import secrets
import logging
from fastapi import APIRouter, Request, HTTPException, Header

from app.api.schemas.request import QueryRequest
from app.api.schemas.response import QueryResponse, TraceInfo

router = APIRouter(tags=["query"])
logger = logging.getLogger(__name__)
API_KEY = (os.getenv("API_KEY") or "").strip()


def _verify_api_key(x_api_key: str | None) -> None:
    # API_KEY가 설정된 환경에서만 인증을 강제한다.
    if not API_KEY:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/query", response_model=QueryResponse)
async def query(
    request: Request,
    body: QueryRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """메인 쿼리 엔드포인트"""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        _verify_api_key(x_api_key)
        executor = request.app.state.executor
        result = await executor.execute(
            query=body.query,
            session_id=body.session_id,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return QueryResponse(
            success=True,
            data={
                "answer": result["answer"],
                "session_id": result["session_id"],
                "citations": [],
            },
            trace=TraceInfo(
                request_id=request_id,
                latency_ms=latency_ms,
            ),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled error in /v1/query (request_id=%s)", request_id)
        raise HTTPException(status_code=500, detail="Internal server error")
