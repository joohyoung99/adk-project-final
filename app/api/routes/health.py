from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    """헬스체크 엔드포인트"""
    return {"status": "ok"}
