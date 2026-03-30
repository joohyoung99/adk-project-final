# ADK 사내 문서 RAG 검색 시스템 (GCP + Vertex AI + ADK)

Google ADK로 만든 CLI 챗봇입니다.

- `filesystem MCP`
- `VertexAI session`
- `Vertex RAG 검색`



## 주요 기능

- Vertex AI 기반 세션 생성
- Gemini 모델을 사용하는 ADK `LlmAgent`
- Vertex RAG Corpus 검색
- MCP Filesystem 서버 연결 준비
- 툴 호출 로그 출력

## 데이터 구조

기존 README에 있던 예시 데이터 구조는 아래와 같습니다.

```json
{
  "doc_id": "projA_001",
  "content": "실시간 알림 시스템은 Kafka 기반으로...",
  "metadata": {
    "project": "A 프로젝트",
    "customer": "삼성",
    "type": "기능",
    "date": "2024",
    "stack": ["Kafka", "Spring"],
    "source": "A_설계서.pdf"
  }
}
```

## 프로젝트 구조

```text
.
├── main.py                         # CLI 실행 진입점
├── agent.py                        # root_agent export
├── app/
│   ├── agent/
│   │   ├── root.py                 # SupervisorAgent 정의
│   │   ├── workflows.py            # sequential/parallel workflow 정의
│   │   └── sub_agents.py           # RAG 검색/병합/저장용 서브에이전트
│   ├── scripts/
│   │   └── create_agent_engine.py  # Agent Engine 생성용 스크립트
│   ├── config/
│   │   └── settings.py             # .env 로드 및 설정값 관리
│   ├── mcp/
│   │   └── toolsets.py             # Filesystem MCP toolset
│   ├── prompt/
│   │   └── instructions.py         # 각 agent prompt
│   ├── services/
│   │   ├── chat_cli.py             # 채팅 루프, session 생성, event 출력
│   │   └── runtime_logging.py      # tool call logging callback
│   └── tool/
│       └── callbacks.py            # callback 연결
└── secrets/

```

## 요구 사항

- Python 3.13+
- Node.js / `npx`
- Google Cloud 프로젝트
- Vertex AI 사용 가능한 GCP 인증

`app/mcp/toolsets.py`에서 `npx @modelcontextprotocol/server-filesystem`를 사용하므로, Filesystem MCP를 쓰려면 Node 환경이 필요합니다.

## 설치

의존성 정의는 [pyproject.toml](/home/pachu/works/adk-project-final/pyproject.toml)에 있습니다.

예시:

```bash
uv sync
```




추가로 GCP 인증이 필요합니다. 일반적으로 아래 둘 중 하나를 맞춰야 합니다.

- `gcloud auth application-default login`
- `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json`



## 실행

CLI 실행:

```bash
python3 main.py
```


## 에이전트 구조

현재 구조는 `SupervisorAgent`가 사용자 질의를 보고 3개의 파이프라인 중 하나로 라우팅하는 형태입니다.

### 1. Root Agent

[app/agent/root.py](/app/agent/root.py)

- 루트 에이전트는 `SupervisorAgent` 하나입니다.
- 타입은 `LlmAgent`이며 모델은 `settings.model`을 사용합니다.
- `supervisor_instruction`을 통해 반드시 아래 3개 파이프라인 중 하나만 선택하도록 강제합니다.
  - `run_sequential_docu_summary_pipeline`
  - `run_parallel_tech_compare_pipeline`
  - `run_sequential_rag_pipeline`
- `before_agent_callback`이 연결되어 있어, 사내 문서/프로젝트 관련 질문이 아니면 실행 전에 차단합니다.

라우팅 기준은 다음과 같습니다.

- 첨부 파일이나 긴 문서 본문 요약 요청: `run_sequential_docu_summary_pipeline`
- 사내 문서/내부 기술 자료 검색 요청: `run_sequential_rag_pipeline`
- 사내 문서와 외부 웹 최신 정보의 비교/보완 요청: `run_parallel_tech_compare_pipeline`

### 2. Workflow 계층

[app/agent/workflows.py](/app/agent/workflows.py)

각 파이프라인은 ADK의 `SequentialAgent` 또는 `ParallelAgent` 조합으로 구성됩니다.

#### `run_sequential_docu_summary_pipeline()`

- 타입: `SequentialAgent`
- 실행 순서:
  1. `DocuRewriteAgent`
  2. `DocuGenerationAgent`

역할:

- 사용자의 요약 요청을 문서 요약용 지시문으로 재작성
- 필요 시 filesystem MCP로 파일을 읽은 뒤 요약 생성

#### `run_sequential_rag_pipeline()`

- 타입: `SequentialAgent`
- 실행 순서:
  1. `RagRewriteAgent`
  2. `RAGSearchAgent`
  3. `RagAnswerAgent`

역할:

- 사용자 질문을 검색형 질의로 재작성
- `search_vertex_rag` 도구로 Vertex RAG corpus 검색
- 검색 결과만 근거로 최종 답변 생성

#### `run_parallel_tech_compare_pipeline()`

- 타입: `SequentialAgent`
- 실행 순서:
  1. `ParallelRewriteAgent`
  2. `ParallelCollectAgent`
  3. `ParallelMergeAgent`
  4. `ParallelAnswerAgent`

이 중 `ParallelCollectAgent`는 내부적으로 `ParallelAgent`이며 아래 두 검색을 동시에 수행합니다.

- `ParallelWebSearchAgent`
- `ParallelRAGSearchAgent`

역할:

- 질문을 검색형 질의로 정리
- 웹 검색과 Vertex RAG 검색을 병렬 수집
- 두 결과를 병합
- 내부 문서 근거와 외부 최신 정보를 함께 반영한 답변 생성

### 3. Sub Agent 상세

[app/agent/sub_agents.py](/app/agent/sub_agents.py)

현재 서브 에이전트는 아래처럼 나뉩니다.

#### 문서 요약 파이프라인

- `DocuRewriteAgent`
  - 출력 키: `docu_rewrite`
  - 사용자의 요약 요청을 다음 단계용 지시문으로 변환
- `DocuGenerationAgent`
  - 도구: `filesystem_toolset`
  - 출력 키: `summary`
  - 파일 경로가 포함된 요청이면 MCP filesystem 도구로 파일을 읽고 요약 생성
  - `after_agent_callback`으로 요약 구조를 후검증

#### RAG 파이프라인

- `RagRewriteAgent`
  - 출력 키: `rag_rewrite`
  - RAG 검색에 적합한 질의로 재작성
- `RAGSearchAgent`
  - 도구: `search_vertex_rag`
  - 출력 키: `rag_result`
  - Vertex RAG corpus 검색 수행
- `RagAnswerAgent`
  - 출력 키: `answer`
  - 검색 결과 기반 최종 답변 생성
  - `after_agent_callback`으로 근거 기반 응답 여부 검증

#### 병렬 비교 파이프라인

- `ParallelRewriteAgent`
  - 출력 키: `parallel_rewrite`
  - 웹 검색과 RAG 검색 공용 질의 생성
- `ParallelWebSearchAgent`
  - 도구: `google_search`
  - 출력 키: `parallel_web_result`
  - 외부 공개 정보 검색
- `ParallelRAGSearchAgent`
  - 도구: `search_vertex_rag`
  - 출력 키: `parallel_rag_result`
  - 내부 문서 검색
- `ParallelMergeAgent`
  - 출력 키: `parallel_merged_result`
  - 웹/RAG 결과를 비교 가능한 형태로 병합
- `ParallelAnswerAgent`
  - 출력 키: `parallel_answer`
  - 병합 결과를 기반으로 최종 비교 답변 생성
  - `after_agent_callback`으로 비교/추천 형식 검증

### 4. 상태 전달 방식

파이프라인 내부 에이전트들은 ADK state에 저장되는 `output_key`를 통해 결과를 다음 단계로 넘깁니다.

- 문서 요약: `docu_rewrite` -> `summary`
- RAG: `rag_rewrite` -> `rag_result` -> `answer`
- 병렬 비교: `parallel_rewrite` -> `parallel_web_result` / `parallel_rag_result` -> `parallel_merged_result` -> `parallel_answer`

### 5. 콜백 역할

[app/tool/callbacks.py](/app/tool/callbacks.py)

- `before_agent_callback`
  - 사용자 질문을 `user_query`로 state에 저장
  - 사내 문서/프로젝트 관련 키워드가 없으면 루트 단계에서 응답 차단
- `after_agent_callback`
  - `RagAnswerAgent`: 추측성 표현 여부, grounding 문구, 검색 결과 존재 여부 검증
  - `DocuGenerationAgent`: 요약 결과 최소 구조 검증
  - `ParallelAnswerAgent`: 비교/추천 형식 검증



## RAG 검색 방식

`search_vertex_rag(query: str)`는 `google.genai.Client(vertexai=True, ...)`를 사용해 `generate_content(...)` 호출 안에 retrieval tool을 붙이는 방식입니다.

설정 포인트:

- corpus: `VERTEX_RAG_CORPUS`
- top-k: `5`
- vector distance threshold: `0.3`
- ranking model: `semantic-ranker-512`

RAG 검색에 필요한 값이 비어 있으면 문자열 에러 메시지를 반환하도록 되어 있습니다.

## MCP Filesystem

[app/mcp/toolsets.py]

Filesystem MCP 서버는 아래 명령으로 연결되도록 정의돼 있습니다.

```bash
npx -y @modelcontextprotocol/server-filesystem <allowed_dir>
```

허용된 tool:

- `read_file`
- `read_multiple_files`
- `list_directory`
- `directory_tree`
- `search_files`
- `get_file_info`
- `write_file`
- `edit_file`
- `create_directory`
- `list_allowed_directories`

## 로그 출력

[app/services/runtime_logging.py]

현재 출력되는 정보:

- agent 이름
- tool 이름
- tool 인자

또한 `chat_cli.py`에서 함수 호출과 함수 응답을 별도로 출력합니다.

## 예시 질문

- Kafka 기반 실시간 알림 시스템 구현 사례
- 캠페인 사례 보여줘
- AI Agent 최신 기술이랑 사내 보유 기술사례 비교하고 추천해줘



## 주요 파일

- [main.py](/main.py)
- [agent.py](/agent.py)
- [app/config/settings.py](app/config/settings.py)
- [app/services/chat_cli.py](app/services/chat_cli.py)
- [app/agent/root.py](/app/agent/root.py)
- [app/agent/workflows.py](app/agent/workflows.py)
- [app/agent/sub_agents.py](app/agent/sub_agents.py)
- [app/mcp/toolsets.py](app/mcp/toolsets.py)
- [app/prompt/instructions.py](app/prompt/instructions.py)


