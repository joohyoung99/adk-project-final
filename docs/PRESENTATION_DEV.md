# ADK Internal Knowledge Agent
## 개발자 기술 발표

---

# 목차

1. 프로젝트 개요
2. 기술 스택
3. 시스템 아키텍처
4. 멀티에이전트 설계
5. 핵심 코드 구조
6. GCP 서비스 연동
7. 배포 파이프라인
8. 개발 중 이슈 및 해결
9. 향후 개선 방향

---

# 1. 프로젝트 개요

## 목표
사내 문서 기반 AI 질의응답 시스템 구축

## 핵심 기능
| 기능 | 설명 |
|------|------|
| 사내 문서 검색 | Vertex AI Search(Discovery Engine) 기반 RAG |
| 기술 비교 | 내부 문서 + 웹 검색 병렬 처리 후 비교 |
| GitHub 검색 | MCP 프로토콜 기반 저장소/이슈/PR 검색 |
| 문서 요약 | 업로드 파일 분석 및 요약 |

## 제공 인터페이스
- **CLI**: `python main.py`
- **REST API**: FastAPI 기반 `/v1/query`
- **Web UI**: React + TypeScript

---

# 2. 기술 스택

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│  React 19 + TypeScript + Tailwind CSS + Vite            │
├─────────────────────────────────────────────────────────┤
│                      Backend                            │
│  FastAPI + Python 3.13 + Google ADK                     │
├─────────────────────────────────────────────────────────┤
│                    AI / ML Layer                        │
│  Gemini 2.5 Flash + Vertex AI RAG + Discovery Engine    │
├─────────────────────────────────────────────────────────┤
│                   Infrastructure                        │
│  GCP Cloud Run + Cloud Build + Artifact Registry        │
└─────────────────────────────────────────────────────────┘
```

### 주요 의존성
```toml
# pyproject.toml
dependencies = [
    "google-adk",           # Google Agent Development Kit
    "fastapi",              # REST API 프레임워크
    "uvicorn",              # ASGI 서버
    "python-dotenv",        # 환경변수 관리
    "google-cloud-discoveryengine",  # Discovery Engine SDK
]
```

---

# 3. 시스템 아키텍처

```
┌──────────────┐     ┌───────────────────────────────────────────────────────────┐
│   Client     │     │                    GCP Cloud Run                          │
│  (Web/CLI)   │────▶│  ┌─────────────────────────────────────────────────────┐  │
└──────────────┘     │  │              Docker Container                       │  │
                     │  │  ┌──────────────┐    ┌────────────────────────┐     │  │
                     │  │  │   Nginx      │    │   ADK Agent Engine     │     │  │
                     │  │  │ (UI Static)  │    │  ┌──────────────────┐  │     │  │
                     │  │  └──────────────┘    │  │ SupervisorAgent  │  │     │  │
                     │  │         │            │  │    (Router)      │  │     │  │
                     │  │  ┌──────────────┐    │  └────────┬─────────┘  │     │  │
                     │  │  │   FastAPI    │───▶│           │            │     │  │
                     │  │  │    :8080     │    │  ┌───────┴────────┐   │     │  │
                     │  │  └──────────────┘    │  ▼       ▼        ▼   │     │  │
                     │  │                      │ RAG   Parallel  GitHub│     │  │
                     │  │                      │ Pipeline Pipeline Pipeline│  │  │
                     │  │                      └────────────────────────┘     │  │
                     │  └─────────────────────────────────────────────────────┘  │
                     └───────────────────────────────────────────────────────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     ▼                              ▼                              ▼
              ┌─────────────┐              ┌──────────────┐              ┌──────────────┐
              │ Discovery   │              │  Vertex AI   │              │  Reasoning   │
              │ Engine      │              │  RAG Corpus  │              │  Engine      │
              │ (문서검색)   │              │  (시맨틱검색) │              │  (세션관리)   │
              └─────────────┘              └──────────────┘              └──────────────┘

                     ┌───────────────────────────────────────────────────────────┐
                     │                    CI/CD Pipeline                         │
                     │  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    │
                     │  │  GitHub  │───▶│ Cloud Build  │───▶│  Artifact    │    │
                     │  │  Push    │    │ (Docker Build)│   │  Registry    │    │
                     │  └──────────┘    └──────────────┘    └──────────────┘    │
                     └───────────────────────────────────────────────────────────┘
```

---

# 4. 멀티에이전트 설계

## Google ADK 에이전트 타입

| 타입 | 용도 | 예시 |
|------|------|------|
| `LlmAgent` | 단일 LLM 작업 수행 | QueryRewriteAgent |
| `SequentialAgent` | 순차 실행 파이프라인 | RAG 파이프라인 |
| `ParallelAgent` | 병렬 실행 | 웹+RAG 동시 검색 |
| `AgentTool` | 에이전트를 도구로 래핑 | 파이프라인 호출용 |

## 4개 파이프라인 구조

```
SupervisorAgent (라우터)
    │
    ├─▶ run_sequential_rag_pipeline
    │      RagRewriteAgent → RAGSearchAgent → RagAnswerAgent
    │
    ├─▶ run_parallel_tech_compare_pipeline
    │      RewriteAgent → ParallelCollectAgent → MergeAgent → AnswerAgent
    │                          │
    │                     ┌────┴────┐
    │                     ▼         ▼
    │               WebSearch   RAGSearch
    │               (병렬 실행)
    │
    ├─▶ run_sequential_docu_summary_pipeline
    │      QueryRewriteAgent → DocuGenerationAgent
    │
    └─▶ run_github_search_pipeline
           GitHubRewriteAgent → GitHubSearchAgent → GitHubAnswerAgent
```

---

# 4-1. 파이프라인 코드 예시

## workflows.py - 병렬 파이프라인 정의

```python
def parallel_collect_agent() -> ParallelAgent:
    """웹검색과 RAG 검색을 병렬 수집한다."""
    return ParallelAgent(
        name="ParallelCollectAgent",
        sub_agents=[
            make_parallel_web_search_agent(),
            make_parallel_rag_search_agent()
        ],
    )

def run_parallel_tech_compare_pipeline() -> SequentialAgent:
    return SequentialAgent(
        name="run_parallel_tech_compare_pipeline",
        sub_agents=[
            make_parallel_rewrite_agent(),
            parallel_collect_agent(),      # 병렬 실행
            make_parallel_merge_agent(),
            make_parallel_answer_agent()
        ],
    )

# AgentTool로 래핑하여 SupervisorAgent가 호출 가능하게 함
tech_compare_tool = AgentTool(run_parallel_tech_compare_pipeline())
```

## root.py - SupervisorAgent 정의

```python
supervisor_agent = LlmAgent(
    name="SupervisorAgent",
    model=settings.model,
    instruction=supervisor_instruction,
    tools=[
        docu_summary_tool,
        tech_compare_tool,
        rag_tool,
        github_search_tool
    ],
    before_agent_callback=before_agent_callback,
    before_model_callback=before_model_callback
)
```

---

# 5. 핵심 코드 구조

```
app/
├── agent/                    # 에이전트 정의
│   ├── root.py              # SupervisorAgent (진입점)
│   ├── sub_agents.py        # 개별 에이전트 팩토리
│   └── workflows.py         # 파이프라인 조합
│
├── api/                      # REST API 계층
│   ├── main.py              # FastAPI 앱 생성
│   ├── executor.py          # ADK 실행기
│   ├── routes/
│   │   ├── health.py        # GET /healthz
│   │   └── query.py         # POST /v1/query
│   └── schemas/
│       ├── request.py       # QueryRequest
│       └── response.py      # QueryResponse
│
├── config/
│   └── settings.py          # 환경변수 관리 (dataclass)
│
├── prompt/
│   └── instructions.py      # 모든 에이전트 프롬프트
│
├── tool/
│   └── callbacks.py         # 콜백 (보안검사, 검증)
│
├── util/
│   └── tool.py              # 검색 도구 (RAG, Discovery)
│
└── mcp/
    └── toolsets.py          # GitHub MCP 연결
```

---

# 5-1. ADK Executor 상세

## executor.py - 세션 관리 핵심 로직

```python
class ADKAgentExecutor:
    def __init__(self):
        self._agent = root_agent
        self._app_name = self._agent.name
        session_service = InMemorySessionService()

        # Reasoning Engine이 설정된 경우에만 Vertex 세션 사용
        if settings.google_agent_engine_name:
            self._app_name = settings.google_agent_engine_name
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.reasoning_engine_location,
            )
            session_service = VertexAiSessionService(
                project=settings.google_cloud_project,
                location=settings.reasoning_engine_location,
            )

        self._runner = Runner(
            app_name=self._app_name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=session_service,
            memory_service=InMemoryMemoryService(),
        )
```

## 세션 조회/생성 패턴 (ADK 공식 문서)

```python
async def execute(self, query: str, session_id: str | None, user_id: str):
    # 1. 세션 조회 시도 (session_id가 있는 경우만)
    session = None
    if session_id:
        session = await self._runner.session_service.get_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
        )

    # 2. 세션이 없으면 새로 생성
    if session is None:
        session = await self._runner.session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
        )

    # 3. 에이전트 실행
    async for event in self._runner.run_async(...):
        ...
```

---

# 5-2. 검색 도구 구현

## tool.py - Discovery Engine 검색

```python
def search_datastore(
    query: str,
    filter_expr: str = "",
    page_size: int = 5,
    return_summary: bool = True,
) -> dict[str, Any]:

    # 클라이언트 설정
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    # 검색 요청 구성
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        filter=sanitized_filter_expr,
        page_size=page_size,
        content_search_spec=content_search_spec,
        query_expansion_spec=...,    # 자동 쿼리 확장
        spell_correction_spec=...,   # 자동 맞춤법 교정
    )

    # 3회 재시도 + Vertex RAG 폴백
    for attempt in range(3):
        try:
            pager = client.search(request=request)
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(1 + attempt)

    if pager is None:
        # Discovery Engine 실패 시 Vertex RAG로 폴백
        return search_vertex_rag(query)
```

---

# 5-3. 콜백 시스템

## callbacks.py - 보안 및 검증 계층

```python
# 시크릿 패턴 탐지
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]+"),   # GitHub 토큰
    re.compile(r"AIza[0-9A-Za-z\-_]+"),        # Google API Key
    re.compile(r"sk-[A-Za-z0-9]+"),            # OpenAI Key
)

def before_agent_callback(callback_context: CallbackContext):
    """에이전트 실행 전 검사"""
    user_text = _extract_user_text(callback_context)

    # 도메인 키워드 기반 라우팅 힌트 설정
    if _mentions_internal_doc_keyword(user_text):
        _state_set(callback_context, "internal_doc_mode", "true")
        return None

    # 범위 외 질문 차단
    if _is_obviously_out_of_scope(user_text):
        return _build_model_content("이 에이전트는 사내 문서...")

def after_tool_callback(tool, args, tool_context, tool_response):
    """도구 실행 후 검사"""
    response_text = str(tool_response)

    # 시크릿 탐지
    if _contains_secret(response_text):
        return {"error": "민감정보 감지됨"}
```

---

# 6. GCP 서비스 연동

## 사용 서비스 및 역할

| 서비스 | 역할 | 리전 |
|--------|------|------|
| **Cloud Run** | API 서버 호스팅 | asia-northeast3 |
| **Reasoning Engine** | 세션 관리 | us-central1 |
| **Discovery Engine** | 사내 문서 검색 | global |
| **Vertex AI RAG** | 시맨틱 검색 | asia-northeast3 |
| **Cloud Build** | CI/CD | - |
| **Artifact Registry** | Docker 이미지 저장 | asia-northeast3 |

## 멀티 리전 구성 이슈

```
                    ┌─────────────────┐
                    │   Cloud Run     │
                    │ asia-northeast3 │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Discovery   │  │  Vertex AI   │  │  Reasoning   │
   │   global    │  │ asia-ne3     │  │  us-central1 │ ← 리전 불일치!
   └─────────────┘  └──────────────┘  └──────────────┘
```

### 해결: 리전별 환경변수 분리

```python
# settings.py
google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
reasoning_engine_location: str = os.getenv("REASONING_ENGINE_LOCATION", "us-central1")
vertex_rag_location: str = os.getenv("VERTEX_RAG_LOCATION", "asia-northeast3")
discovery_engine_location: str = os.getenv("DISCOVERY_ENGINE_LOCATION", "global")
```

---

# 7. 배포 파이프라인

## Cloud Build 파이프라인

```yaml
# cloudbuild.yaml
steps:
  # 1. Docker 빌드
  - name: "gcr.io/cloud-builders/docker"
    args: ["build", "--platform=linux/amd64", "-t", "...", "."]

  # 2. Artifact Registry 푸시
  - name: "gcr.io/cloud-builders/docker"
    args: ["push", "--all-tags", "..."]

  # 3. Cloud Run 배포
  - name: "gcr.io/cloud-builders/gcloud"
    args:
      - "run"
      - "deploy"
      - "--set-env-vars=REASONING_ENGINE_LOCATION=${_REASONING_ENGINE_LOCATION},..."
      - "--timeout=180s"
      - "--memory=2Gi"
      - "--cpu=2"

  # 4. 스모크 테스트
  - name: "gcr.io/cloud-builders/gcloud"
    args: ["curl", "/healthz", "/"]
```

## Dockerfile - 멀티스테이지 빌드

```dockerfile
# Stage 1: UI 빌드
FROM node:20-alpine AS ui-builder
COPY ui /ui
RUN npm install && npm run build

# Stage 2: Python 의존성
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN uv sync --frozen --no-dev

# Stage 3: 런타임
FROM python:3.13-slim AS runtime
COPY --from=builder /app /app
COPY --from=ui-builder /ui/dist /app/ui/dist
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

# 7-1. 배포 명령어

## 원클릭 배포

```bash
./deploy_from_env.sh
```

## 수동 배포

```bash
# .env에서 환경변수 추출하여 Cloud Build 실행
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="\
_VERTEX_RAG_CORPUS=$(grep VERTEX_RAG_CORPUS .env | sed 's/.*=//'),\
_DISCOVERY_ENGINE_ENGINE_ID=$(grep DISCOVERY_ENGINE_ENGINE_ID .env | sed 's/.*=//'),\
_REASONING_ENGINE_APP_NAME=$(grep REASONING_ENGINE_APP_NAME .env | sed 's/.*=//'),\
_REASONING_ENGINE_ID=$(grep '^REASONING_ENGINE_ID' .env | sed 's/.*=//'),\
_REASONING_ENGINE_LOCATION=$(grep REASONING_ENGINE_LOCATION .env | sed 's/.*=//')"
```

## 배포 확인

```bash
# 서비스 URL 확인
gcloud run services describe adk-rag-api-dev \
  --region=asia-northeast3 \
  --format='value(status.url)'

# API 테스트
curl -X POST "$SERVICE_URL/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "사내 보안 정책 알려줘", "user_id": "dev-test"}'
```

---

# 8. 개발 중 이슈 및 해결

## 이슈 1: Reasoning Engine 세션 연동 오류

```
Error: App name SupervisorAgent is not valid.
It should be the full ReasoningEngine resource name.
```

**원인**: ADK의 VertexAiSessionService는 Reasoning Engine 리소스 전체 경로 필요

**해결**:
```python
# Before
app_name = "SupervisorAgent"

# After
app_name = "projects/{project}/locations/{location}/reasoningEngines/{id}"
```

---

## 이슈 2: 리전 불일치 404 오류

```
POST https://asia-northeast3-aiplatform.googleapis.com/.../reasoningEngines/...
→ 404 Not Found
```

**원인**: Reasoning Engine은 us-central1에 있는데, Cloud Run 리전(asia-northeast3)으로 요청

**해결**:
```python
# Reasoning Engine 전용 리전 환경변수 추가
vertexai.init(
    project=settings.google_cloud_project,
    location=settings.reasoning_engine_location,  # us-central1
)
```

---

## 이슈 3: 세션 생성 시 Null 처리 오류

```
GET .../sessions/None → 400 Bad Request
```

**원인**: 신규 사용자(session_id 없음) 요청 시 `get_session(session_id=None)` 호출

**해결**: ADK 공식 문서 패턴 적용
```python
# 1. session_id가 있을 때만 조회
session = None
if session_id:
    session = await session_service.get_session(session_id=session_id)

# 2. 없으면 새로 생성
if session is None:
    session = await session_service.create_session(user_id=user_id)
```

---

## 이슈 4: Cloud Run 타임아웃

**문제**: 멀티에이전트 체인 실행 시 60초 초과 → 504 Gateway Timeout

**해결**:
```yaml
# cloudbuild.yaml
_TIMEOUT: "180s"  # 60s → 180s
```

---

## 이슈 5: 환경변수 파싱 오류

**문제**:
```bash
# .env 파일
VERTEX_RAG_CORPUS = "projects/..."  # 공백, 따옴표 포함

# Cloud Run 환경변수
VERTEX_RAG_CORPUS: ' "projects/..."'  # 오류 발생
```

**해결**: .env 파일 형식 표준화
```bash
# 수정 후
VERTEX_RAG_CORPUS=projects/...  # 공백/따옴표 제거
```

---

# 9. 향후 개선 방향

## 단기 개선

| 항목 | 설명 |
|------|------|
| 스트리밍 응답 | SSE를 통한 실시간 응답 제공 |
| Citation 반환 | API 응답에 출처 정보 포함 |
| 에러 처리 고도화 | 구조화된 에러 응답 |

## 중기 개선

| 항목 | 설명 |
|------|------|
| callbacks.py 모듈화 | 보안/검증 로직 분리 |
| async I/O 전환 | Discovery Engine 동기 호출 개선 |
| 캐싱 도입 | 반복 쿼리 성능 향상 |

## 장기 개선

| 항목 | 설명 |
|------|------|
| Observability | Cloud Monitoring + Trace 연동 |
| A/B 테스트 | 프롬프트/모델 성능 비교 |
| Fine-tuning | 도메인 특화 모델 학습 |

---

# 참고 자료

- [Google ADK 공식 문서](https://cloud.google.com/vertex-ai/docs/agent-development-kit)
- [Vertex AI RAG API](https://cloud.google.com/vertex-ai/docs/generative-ai/rag-overview)
- [Discovery Engine API](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction)
- [Cloud Run 배포 가이드](https://cloud.google.com/run/docs/deploying)

---

# Q&A

## 예상 질문

**Q: 왜 LangChain 대신 Google ADK를 선택했나요?**
> GCP 서비스들과 네이티브 통합 지원. 특히 Vertex AI 세션 서비스, Reasoning Engine과의 연동이 ADK에서 더 안정적입니다.

**Q: 응답 시간(~15초)을 줄일 수 있나요?**
> 현재 멀티에이전트 체인 구조상 한계가 있습니다. 스트리밍 응답 도입으로 체감 시간 단축 가능합니다.

**Q: 에이전트 간 데이터는 어떻게 전달되나요?**
> ADK의 state와 output_key를 통해 전달됩니다. 예: RagRewriteAgent의 output_key="rag_rewrite"가 다음 에이전트에서 {{rag_rewrite}}로 참조됩니다.

**Q: 새로운 파이프라인 추가는 어떻게 하나요?**
> 1. sub_agents.py에 에이전트 팩토리 추가
> 2. workflows.py에 파이프라인 정의
> 3. root.py의 tools에 AgentTool 등록
> 4. supervisor_instruction에 라우팅 규칙 추가

---

# 감사합니다

**프로젝트 저장소**: `adk-project-final/`

**문의**: [팀 채널]
