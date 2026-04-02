#!/bin/bash
# 로컬 API 서버 실행 스크립트

set -e

echo "=== ADK RAG API 로컬 서버 시작 ==="
echo ""

# .env 파일 확인
if [ ! -f .env ]; then
    echo "Error: .env 파일이 없습니다."
    exit 1
fi

# 포트 설정 (기본: 8080)
PORT=${API_PORT:-8080}

echo "포트: $PORT"
echo "Swagger UI: http://localhost:$PORT/docs"
echo ""

# uvicorn 실행
uv run uvicorn app.api.main:app --host 0.0.0.0 --port $PORT --reload
