# SPEC.md - ADK + FastAPI + GCP + Vertex AI Search 시스템 설계

> **버전**: v1.1
> **최종 수정**: 2026-04-01
> **담당**: yhcho (FastAPI 구현 + GCP 연동 + 빌드 자동화)


## 1. 목표

사용자 질의 → **FastAPI** → **ADK 에이전트** → **Vertex AI Search** → 답변 생성 → **Cloud Run** 배포

---

## 2. 프로젝트 구조 (목표)

```
adk-project-final/
├── main.py                      # CLI 진입점 (기존 유지)
├── agent.py                     # root_agent export (기존 유지)
├── app/
│   ├── api/                     # [신규] FastAPI 계층
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 앱 생성, uvicorn 실행
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py        # /healthz
│   │   │   ├── query.py         # /v1/query
│   │   │   └── session.py       # /v1/sessions (선택)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── request.py       # Pydantic 요청 모델
│   │   │   └── response.py      # Pydantic 응답 모델
│   │   └── executor.py          # ADK Agent 실행기
│   ├── agent/                   # 기존 에이전트 (유지)
│   │   ├── root.py
│   │   ├── sub_agents.py
│   │   └── workflows.py
│   ├── config/
│   │   └── settings.py          # 환경변수 관리
│   ├── mcp/
│   │   └── toolsets.py
│   ├── prompt/
│   │   └── instructions.py
│   ├── services/
│   │   ├── chat_cli.py          # CLI 채팅 (기존 유지)
│   │   └── runtime_logging.py
│   └── tool/
│       └── callbacks.py
├── Dockerfile                   # [신규] 멀티스테이지 빌드
├── .dockerignore                # [신규]
├── env-sample                   # [신규] 환경변수 템플릿
├── cloudbuild.yaml              # [신규] Cloud Build 설정
├── pyproject.toml
└── uv.lock
```

---

## 3. FastAPI 구현 명세

### 3.1 app/api/main.py

```python
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import health, query
from app.api.executor import ADKAgentExecutor

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 에이전트 실행기 초기화
    app.state.executor = ADKAgentExecutor()
    yield
    # Shutdown: 정리 작업

def create_app() -> FastAPI:
    app = FastAPI(
        title="ADK RAG API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 프로덕션에서는 구체적 도메인 지정
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(health.router)
    app.include_router(query.router, prefix="/v1")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8080")),
        workers=int(os.getenv("UVICORN_WORKERS", "1")),
        reload=os.getenv("ENV", "dev") == "dev",
    )
```

### 3.2 app/api/executor.py

```python
from typing import AsyncIterable, Optional
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types

from app.agent.root import root_agent
from app.config.settings import settings

class ADKAgentExecutor:
    """ADK 에이전트 실행기 (nh-poc-matsun ADKAgentExecutor 참조)"""

    def __init__(self):
        self._agent = root_agent
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def execute(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> dict:
        """동기 실행: 최종 응답만 반환"""
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # 세션 생성 또는 조회
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=user_id,
                state={},
                session_id=session_id,
            )

        # 에이전트 실행
        final_response = None
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                break

        return {
            "answer": final_response or "응답을 생성할 수 없습니다.",
            "session_id": session.id,
        }

    async def stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> AsyncIterable[dict]:
        """스트리밍 실행: 중간 업데이트 포함"""
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=user_id,
                state={},
                session_id=session_id,
            )

        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                    yield {"is_final": True, "content": response}
            else:
                yield {"is_final": False, "content": "처리 중..."}
```

### 3.3 app/api/routes/query.py

```python
import uuid
import time
from typing import Optional
from fastapi import APIRouter, Request, HTTPException

from app.api.schemas.request import QueryRequest
from app.api.schemas.response import QueryResponse, TraceInfo

router = APIRouter(tags=["query"])

@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    """메인 쿼리 엔드포인트"""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
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
                "citations": [],  # TODO: 검색 결과에서 추출
            },
            trace=TraceInfo(
                request_id=request_id,
                latency_ms=latency_ms,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3.4 app/api/schemas/request.py

```python
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="사용자 질의", min_length=1)
    session_id: Optional[str] = Field(None, description="세션 ID")
    top_k: int = Field(5, ge=1, le=20, description="검색 결과 수")
    filters: Optional[Dict[str, Any]] = Field(None, description="검색 필터")
```

### 3.5 app/api/schemas/response.py

```python
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
```

---

## 4. Dockerfile (멀티스테이지 빌드)

```dockerfile
# --- 빌드 스테이지 ---
FROM python:3.13-slim-bookworm AS builder

# uv 바이너리 복사
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 빌드 최적화 환경변수
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 의존성 파일 복사 및 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 소스 코드 복사
COPY . /app

# --- 실행 스테이지 ---
FROM python:3.13-slim-bookworm AS runtime

# 빌드 결과 복사
COPY --from=builder /app /app

# 환경변수 설정
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 포트 노출
EXPOSE 8080

# 실행
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 5. .dockerignore

```
.venv/
.git/
.gitignore
.vscode/
.qodo/
__pycache__/
*.pyc
*.pyo
.DS_Store
.env
*.md
Dockerfile
.dockerignore
```

---

## 6. env-sample

```bash
# === GCP 설정 ===
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# === Vertex AI 설정 ===
GOOGLE_GENAI_USE_VERTEXAI=1
# Vertex AI Search (Vertex AI Search 사용 시)
VERTEX_SEARCH_ENGINE_ID=
VERTEX_SEARCH_DATASTORE_ID=
# Vertex RAG Corpus (기존 RAG 사용 시)
VERTEX_RAG_LOCATION=asia-northeast3
VERTEX_RAG_CORPUS=

# === 에이전트 설정 ===
ROOT_AGENT_NAME=SupervisorAgent
MODEL_GEMINI_2_5_FLASH=gemini-2.5-flash

# === GitHub MCP (선택) ===
GITHUB_MCP_SERVER_PATH=
GITHUB_PERSONAL_ACCESS_TOKEN=

# === 서버 설정 ===
API_HOST=0.0.0.0
API_PORT=8080
UVICORN_WORKERS=4
LOG_LEVEL=INFO
ENV=dev

# === 프로덕션 환경 (선택) ===
# GCS_ARTIFACT_SERVICE=bucket-name
# DATABASE_SESSION_SERVICE=postgresql://user:pass@host:5432/db
# VERTEXAIRAG_MEMORY_SERVICE=projects/{project}/locations/{location}/ragCorpora/{id}
```

---

## 7. pyproject.toml 수정

```toml
[project]
name = "adk-rag-api"
version = "0.1.0"
description = "ADK RAG API with FastAPI"
readme = "README.md"
requires-python = ">=3.13"

dependencies = [
    "asyncpg>=0.31.0",
    "dotenv>=0.9.9",
    "fastapi>=0.115.0",
    "fastmcp>=3.1.1",
    "google-adk>=1.16.0",
    "google-cloud-discoveryengine>=0.13.0",
    "httpx>=0.28.1",
    "pydantic>=2.10.0",
    "python-dotenv>=1.2.2",
    "uvicorn[standard]>=0.34.0",
]

[project.scripts]
adk-rag-cli = "main:main"
adk-rag-api = "app.api.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 8. cloudbuild.yaml

```yaml
steps:
  # 1. Docker 이미지 빌드
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--platform=linux/amd64'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}:latest'
      - '.'

  # 2. Artifact Registry 푸시
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}'

  # 3. Cloud Run 배포
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - '${_SERVICE}-${_ENV}'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--service-account=${_RUN_SA}'
      - '--set-env-vars=GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${_REGION},GOOGLE_GENAI_USE_VERTEXAI=1,LOG_LEVEL=${_LOG_LEVEL},ENV=${_ENV}'
      - '--min-instances=${_MIN_INSTANCES}'
      - '--max-instances=${_MAX_INSTANCES}'
      - '--memory=${_MEMORY}'
      - '--cpu=${_CPU}'
      - '--timeout=${_TIMEOUT}'
      - '--concurrency=${_CONCURRENCY}'
      - '--allow-unauthenticated'

  # 4. Smoke Test
  - name: 'gcr.io/cloud-builders/gcloud'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        SERVICE_URL=$(gcloud run services describe ${_SERVICE}-${_ENV} --region=${_REGION} --format='value(status.url)')
        curl -sf "$${SERVICE_URL}/healthz" || exit 1
        echo "✅ Smoke test passed!"

substitutions:
  _REGION: 'asia-northeast3'
  _REPO: 'adk-rag-repo'
  _SERVICE: 'adk-rag-api'
  _ENV: 'dev'
  _RUN_SA: 'cloudrun-sa@${PROJECT_ID}.iam.gserviceaccount.com'
  _MIN_INSTANCES: '0'
  _MAX_INSTANCES: '10'
  _MEMORY: '2Gi'
  _CPU: '2'
  _TIMEOUT: '60s'
  _CONCURRENCY: '20'
  _LOG_LEVEL: 'INFO'

options:
  logging: CLOUD_LOGGING_ONLY

images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}'
```

---

## 9. GCP 설정 명령어

### 9.1 API 활성화

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com
```

### 9.2 Artifact Registry 생성

```bash
gcloud artifacts repositories create adk-rag-repo \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="ADK RAG API images"
```

### 9.3 서비스 계정 설정

```bash
PROJECT_ID=$(gcloud config get-value project)

# Cloud Run 서비스 계정 생성
gcloud iam service-accounts create cloudrun-sa \
  --display-name="Cloud Run SA"

# 권한 부여
RUN_SA="cloudrun-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/discoveryengine.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/logging.logWriter"
```

### 9.4 Cloud Build 트리거

```bash
# main 브랜치 → dev 배포
gcloud builds triggers create github \
  --name="deploy-dev" \
  --repo-name="adk-project-final" \
  --repo-owner="YOUR_ORG" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENV=dev,_LOG_LEVEL=DEBUG"

# 태그 → prod 배포
gcloud builds triggers create github \
  --name="deploy-prod" \
  --repo-name="adk-project-final" \
  --repo-owner="YOUR_ORG" \
  --tag-pattern="^v[0-9]+\\.[0-9]+\\.[0-9]+$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENV=prod,_MIN_INSTANCES=1"
```

---

## 10. 로컬 개발

### 10.1 의존성 설치

```bash
uv sync
```

### 10.2 환경변수 설정

```bash
cp env-sample .env
# .env 파일 편집
```

### 10.3 실행

```bash
# CLI 모드 (기존)
uv run python main.py

# API 모드 (신규)
uv run uvicorn app.api.main:app --reload --port 8080
```

### 10.4 Docker 로컬 테스트

```bash
# 빌드
docker buildx build --platform=linux/amd64 -t adk-rag-api:local .

# 실행
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  -e GOOGLE_GENAI_USE_VERTEXAI=1 \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  adk-rag-api:local
```

---

## 11. API 엔드포인트 요약

| Method | Path | 설명 |
|--------|------|------|
| GET | `/healthz` | 헬스체크 |
| POST | `/v1/query` | 메인 쿼리 (자동 라우팅) |
| GET | `/v1/sessions` | 세션 목록 (선택) |
| GET | `/v1/sessions/{id}` | 세션 상세 (선택) |

---

## 12. 구현 순서

1. **[Phase 1]** FastAPI 기본 구조
   - [x] `app/api/main.py` 생성
   - [x] `app/api/routes/health.py` 생성
   - [x] `app/api/executor.py` 생성
   - [x] 로컬 테스트

2. **[Phase 2]** 쿼리 엔드포인트
   - [x] `app/api/schemas/` 생성
   - [x] `app/api/routes/query.py` 생성
   - [x] ADK 에이전트 연동 테스트

3. **[Phase 3]** Docker + GCP
   - [x] `Dockerfile` 생성
   - [x] `.dockerignore` 생성
   - [x] `env-sample` 생성
   - [x] 로컬 Docker 테스트

4. **[Phase 4]** Cloud Build + Cloud Run
   - [x] `cloudbuild.yaml` 생성
   - [x] GCP 리소스 설정
   - [x] dev 환경 배포
   - [x] Smoke test

5. **[Phase 5]** 프로덕션
   - [ ] prod 환경 배포
   - [ ] 모니터링/알림 설정
   - [ ] 문서화


