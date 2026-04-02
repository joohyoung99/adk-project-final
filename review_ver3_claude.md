# ADK Internal Knowledge Agent - 코드 리뷰 v3

> **리뷰어**: Senior Backend Developer / Tech Lead
> **리뷰 일자**: 2026-04-02
> **대상 브랜치**: yhjo
> **프로젝트**: Google ADK 기반 멀티에이전트 RAG 시스템

---

## 📊 평가 점수표

| 항목 | 점수 | 코멘트 |
|------|:----:|--------|
| **아키텍처** | B+ | 멀티에이전트 파이프라인 구조 우수, 일부 결합도 개선 필요 |
| **코드 품질** | B | 타입 힌트 적용 양호, 일부 중복 코드 및 과도한 콜백 로직 |
| **GCP/ADK 활용** | B+ | 공식 문서 패턴 준수, 리전 처리 및 폴백 구현 적절 |
| **유지보수성** | B | 관심사 분리 양호, callbacks.py 파일 분할 권장 |
| **보안** | B+ | 시크릿 탐지 및 API 키 검증 구현, 환경변수 노출 주의 필요 |

---

## 👍 잘한 점

### 1. 멀티에이전트 아키텍처 설계 (root.py, workflows.py)

```python
# workflows.py:37-48
def run_parallel_tech_compare_pipeline() -> SequentialAgent:
    return SequentialAgent(
        name="run_parallel_tech_compare_pipeline",
        sub_agents=[
            make_parallel_rewrite_agent(),
            parallel_collect_agent(),  # ParallelAgent 내부에서 웹+RAG 병렬 실행
            make_parallel_merge_agent(),
            make_parallel_answer_agent()
        ],
    )
```

- ADK의 `SequentialAgent`와 `ParallelAgent`를 적절히 조합하여 4개의 명확한 파이프라인 구성
- SupervisorAgent가 단일 진입점 역할을 하며 라우팅 책임만 담당
- 각 에이전트가 단일 책임 원칙(SRP)을 잘 준수함

### 2. Vertex AI 세션 관리 패턴 (executor.py:50-71)

```python
# ADK 공식 문서 패턴을 정확히 따름
session = None
if session_id:
    session = await self._runner.session_service.get_session(
        app_name=self._app_name,
        user_id=user_id,
        session_id=session_id,
    )
if session is None:
    session = await self._runner.session_service.create_session(
        app_name=self._app_name,
        user_id=user_id,
    )
```

- `session_id=None` 케이스를 정확히 처리하여 400 Bad Request 방지
- InMemory 폴백과 Vertex 세션 서비스를 조건부로 선택하는 구조 우수

### 3. Discovery Engine 폴백 전략 (tool.py:251-290)

```python
# Discovery Engine 장애 시 Vertex RAG로 폴백
if pager is None:
    fallback_answer = search_vertex_rag(query)
    if fallback_answer and not fallback_answer.startswith("Vertex RAG 검색 실패"):
        logger.error("discovery_search_fallback_used ...")
        return { "summary": fallback_answer, ... }
```

- 3회 재시도 + RAG 폴백으로 가용성 확보
- 메트릭 로깅으로 장애 추적 가능

### 4. 보안 정책 적용 (callbacks.py:154-159, 251-254)

```python
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]+"),   # GitHub 토큰
    re.compile(r"AIza[0-9A-Za-z\-_]+"),        # Google API Key
    re.compile(r"sk-[A-Za-z0-9]+"),            # OpenAI Key
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)

def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)
```

- 다양한 시크릿 패턴 탐지
- before_model_callback, after_tool_callback에서 중복 검증

### 5. 환경 설정 분리 (settings.py)

```python
@dataclass(frozen=True, slots=True)
class Settings:
    reasoning_engine_location: str = os.getenv(
        "REASONING_ENGINE_LOCATION",
        os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
```

- `frozen=True, slots=True`로 불변성 및 메모리 효율성 확보
- 리전별 환경변수 분리로 멀티리전 배포 대응

### 6. Docker 멀티스테이지 빌드 (Dockerfile)

```dockerfile
FROM node:20-alpine AS ui-builder
FROM python:3.13-slim-bookworm AS builder
FROM python:3.13-slim-bookworm AS runtime
```

- UI/Python/Runtime 분리로 최종 이미지 크기 최소화
- `uv` 패키지 매니저 활용으로 빌드 속도 향상

### 7. API 키 검증의 타이밍 세이프 비교 (query.py:20)

```python
if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
    raise HTTPException(status_code=401, detail="Unauthorized")
```

- `secrets.compare_digest` 사용으로 타이밍 공격 방지

---

## ⚠️ 개선 필요

### 1. [Critical] CLI와 API의 세션 초기화 로직 중복

**위치**: `app/services/chat_cli.py:54-62` vs `app/api/executor.py:24-33`

**문제점**:
```python
# chat_cli.py - CLI용
vertexai.init(
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,  # ❌ 잘못된 리전
)
session_service = VertexAiSessionService(
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,  # ❌ reasoning_engine_location이어야 함
)

# executor.py - API용
vertexai.init(
    project=settings.google_cloud_project,
    location=settings.reasoning_engine_location,  # ✅ 올바름
)
```

**영향**: CLI 실행 시 Reasoning Engine이 다른 리전에 있으면 404 오류 발생

**개선 방법**:
```python
# app/services/session_factory.py (새 파일)
def create_session_service() -> VertexAiSessionService | InMemorySessionService:
    if settings.google_agent_engine_name:
        vertexai.init(
            project=settings.google_cloud_project,
            location=settings.reasoning_engine_location,
        )
        return VertexAiSessionService(
            project=settings.google_cloud_project,
            location=settings.reasoning_engine_location,
        )
    return InMemorySessionService()
```

---

### 2. [High] callbacks.py 파일 크기 및 책임 과다 (682 라인)

**위치**: `app/tool/callbacks.py`

**문제점**:
- 단일 파일에 7개 이상의 책임 혼재
- 도메인 판별, 보안 검사, 응답 검증, 상태 관리가 모두 한 곳에
- 테스트 및 유지보수 어려움

**개선 방법**: 기능별 모듈 분리
```
app/tool/
├── callbacks/
│   ├── __init__.py          # 외부 export
│   ├── security.py          # 시크릿 탐지, sanitize
│   ├── domain_routing.py    # 내부문서/GitHub 키워드 판별
│   ├── validators/
│   │   ├── rag_validator.py
│   │   ├── github_validator.py
│   │   └── summary_validator.py
│   └── state_utils.py       # state get/set 유틸
```

---

### 3. [High] search_vertex_rag의 location 파라미터 불일치

**위치**: `app/util/tool.py:32-34`

**문제점**:
```python
project = settings.google_cloud_project
location = settings.google_cloud_location  # ❌ vertex_rag_location이어야 함
rag_corpus = settings.vertex_rag_corpus
```

RAG corpus가 `asia-northeast3`에 있는데, `google_cloud_location`(us-central1)으로 호출하면 리소스를 찾을 수 없음

**개선 방법**:
```python
location = settings.vertex_rag_location  # ✅ RAG 전용 리전 사용
```

---

### 4. [Medium] 동기 blocking I/O in async context

**위치**: `app/util/tool.py:234-249`

**문제점**:
```python
for attempt in range(3):
    try:
        pager = client.search(request=request)  # ❌ 동기 호출
        break
    except Exception as e:
        time.sleep(1 + attempt)  # ❌ 동기 sleep
```

async 컨텍스트에서 동기 I/O 호출은 이벤트 루프를 블로킹함

**개선 방법**:
```python
import asyncio

async def search_datastore_async(...) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    for attempt in range(3):
        try:
            pager = await loop.run_in_executor(None, lambda: client.search(request=request))
            break
        except Exception as e:
            await asyncio.sleep(1 + attempt)
```

또는 Discovery Engine의 async client가 있다면 해당 사용 권장

---

### 5. [Medium] 하드코딩된 매직 넘버들

**위치**: 여러 파일

**문제점**:
```python
# tool.py
rag_retrieval_config=types.RagRetrievalConfig(
    top_k=5,                              # 매직 넘버
    vector_distance_threshold=0.3,        # 매직 넘버
)

# callbacks.py
if len(user_text) <= 8:                   # 매직 넘버
if len(normalized) < 8:                   # 매직 넘버
```

**개선 방법**: settings.py 또는 constants.py로 추출
```python
# app/config/constants.py
RAG_TOP_K = 5
RAG_DISTANCE_THRESHOLD = 0.3
MIN_QUERY_LENGTH = 8
```

---

### 6. [Medium] Citation 모델 미사용

**위치**: `app/api/schemas/response.py:5-9`, `app/api/routes/query.py:52`

**문제점**:
```python
# response.py에 정의됨
class Citation(BaseModel):
    doc_id: str
    title: str
    snippet: str
    uri: Optional[str] = None

# query.py에서 항상 빈 리스트
return QueryResponse(
    data={
        "citations": [],  # ❌ 항상 빈 리스트
    }
)
```

검색 결과에 출처 정보가 있지만 API 응답에 반영되지 않음

**개선 방법**: executor.py에서 grounding_metadata 또는 results에서 Citation 추출
```python
def _extract_citations(self, results: list) -> list[Citation]:
    return [
        Citation(
            doc_id=r.get("id", ""),
            title=r.get("title", ""),
            snippet=r.get("snippet", ""),
            uri=r.get("uri"),
        )
        for r in results if r.get("title")
    ]
```

---

### 7. [Medium] GitHub MCP 연결 실패 시 처리 부재

**위치**: `app/mcp/toolsets.py`

**문제점**:
```python
github_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=settings.github_mcp_server_path,  # 경로가 없으면?
            ...
        ),
        timeout=20.0,
    ),
)
```

`github_mcp_server_path`가 비어있거나 유효하지 않으면 import 시점에 오류 또는 런타임 실패

**개선 방법**: Lazy initialization 또는 조건부 생성
```python
def get_github_mcp_toolset() -> MCPToolset | None:
    if not settings.github_mcp_server_path:
        logging.warning("GitHub MCP server path not configured")
        return None
    return MCPToolset(...)
```

---

### 8. [Low] 프롬프트 인스트럭션의 템플릿 변수 불일치

**위치**: `app/prompt/instructions.py`

**문제점**:
```python
# rag_search_instruction
"#입력값:
- query: {{rag_rewrite}}
- filter_expr: {{rag_filter_expr}}"
```

ADK에서 `{{variable}}` 템플릿이 실제로 state에서 치환되는지 확인 필요. ADK는 기본적으로 Jinja2가 아닌 자체 컨텍스트 주입 방식 사용.

**개선 방법**: ADK 공식 문서의 state 참조 방식 확인 후 수정 또는 동적 프롬프트 생성 로직 추가

---

### 9. [Low] Error Response 일관성 부족

**위치**: `app/api/routes/query.py:59-63`

**문제점**:
```python
except HTTPException:
    raise
except Exception:
    logger.exception("Unhandled error")
    raise HTTPException(status_code=500, detail="Internal server error")
```

모든 예외가 동일한 메시지로 반환되어 클라이언트 디버깅 어려움

**개선 방법**: 구조화된 에러 응답
```python
from app.api.schemas.response import QueryResponse, TraceInfo

except Exception as e:
    return QueryResponse(
        success=False,
        data={},
        error=str(e) if settings.env == "dev" else "Internal server error",
        trace=TraceInfo(request_id=request_id, latency_ms=latency_ms),
    )
```

---

### 10. [Low] 로깅 포맷 비일관성

**위치**: `app/util/tool.py:240-244`

**문제점**:
```python
logger.warning(
    "discovery_search_attempt_failed attempt=%d query=%r engine_id=%s error=%s",
    attempt + 1, query[:120], engine_id, str(e),
)
```

일부는 key=value 포맷, 일부는 일반 문자열. 구조화된 로깅 권장.

**개선 방법**: structlog 또는 JSON 로깅 도입
```python
logger.warning(
    "Discovery search failed",
    extra={
        "attempt": attempt + 1,
        "query": query[:120],
        "engine_id": engine_id,
        "error": str(e),
    }
)
```

---

## 🔧 즉시 적용 권장 수정 사항

### 1. chat_cli.py 리전 수정 (Critical)

```python
# app/services/chat_cli.py:54-62
vertexai.init(
    project=settings.google_cloud_project,
    location=settings.reasoning_engine_location,  # 수정
)

session_service = VertexAiSessionService(
    project=settings.google_cloud_project,
    location=settings.reasoning_engine_location,  # 수정
)
```

### 2. tool.py RAG location 수정 (High)

```python
# app/util/tool.py:33
location = settings.vertex_rag_location  # google_cloud_location → vertex_rag_location
```

### 3. settings.py에 env 필드 추가 (Low)

```python
@dataclass(frozen=True, slots=True)
class Settings:
    env: str = os.getenv("ENV", "dev")
    # ... 기존 필드들
```

---

## 📝 종합 의견

이 프로젝트는 Google ADK를 활용한 멀티에이전트 RAG 시스템으로서 **전반적으로 잘 구현**되어 있습니다.

**강점**:
- ADK의 Sequential/Parallel Agent 패턴을 적절히 활용
- 세션 관리, 폴백 전략, 보안 검사 등 프로덕션 고려사항 반영
- CI/CD 파이프라인 및 Docker 빌드 최적화

**개선 포인트**:
- CLI/API 간 세션 초기화 로직 중복 제거 필요
- callbacks.py 모듈 분할로 유지보수성 향상
- 리전 설정 일관성 확보 (RAG corpus용 리전 명확히 구분)

배포 전 **Critical/High 이슈 3개**를 우선 수정하고, Medium 이슈들은 다음 스프린트에서 점진적으로 개선하는 것을 권장합니다.

---

*Reviewed by Claude Opus 4.5 | 2026-04-02*
