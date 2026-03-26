# ADK 사내 문서 RAG 검색 시스템 (GCP + Vertex AI + ADK)

Google ADK로 만든 CLI 챗봇입니다.

- `filesystem MCP`
- `VertexAI session`
- `Vertex RAG 검색`

현재 코드는 Vertex AI Session Service와 Vertex RAG 검색을 중심으로 구성되어 있고, 일부 멀티에이전트 파이프라인은 뼈대만 있는 상태입니다.

## 현재 구현 상태

- CLI 채팅 진입점은 `main.py` 입니다.
- 루트 에이전트는 `SupervisorAgent` 하나로 구성되어 있습니다.
- Vertex AI Session Service를 사용해 세션을 생성합니다.
- Vertex RAG 검색용 서브에이전트가 구현되어 있습니다.
- Filesystem MCP toolset은 정의되어 있지만, 현재 기본 실행 흐름에서는 직접 사용되지 않습니다.
- 일부 프롬프트와 workflow 이름이 실제 함수명과 맞지 않아, 멀티에이전트 라우팅은 아직 정리되지 않은 상태입니다.

즉, 이 저장소는 "완성된 범용 멀티에이전트 앱"보다는 "Vertex AI + ADK + RAG CLI 실험/구축 중인 프로젝트"로 보는 편이 정확합니다.

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
├── scripts/
│   └── create_agent_engine.py      # Agent Engine 생성용 일회성 스크립트
├── app/
│   ├── agent/
│   │   ├── root.py                 # SupervisorAgent 정의
│   │   ├── workflows.py            # sequential/parallel workflow 정의
│   │   └── sub_agents.py           # RAG 검색/병합/저장용 서브에이전트
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
    └── gcp_account_credentials.json
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

또는 사용 중인 환경에 맞게 `pip`로 설치해도 됩니다.

## 환경 변수

루트 `.env` 파일을 사용합니다. 현재 코드가 읽는 값은 아래와 같습니다.

| 변수명 | 필수 여부 | 설명 |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | 필수 | GCP 프로젝트 ID |
| `GOOGLE_CLOUD_LOCATION` | 권장 | Vertex AI 위치. 기본값 `us-central1` |
| `MODEL_GEMINI_2_5_FLASH` | 선택 | 기본 모델명. 기본값 `gemini-2.5-flash` |
| `VERTEX_RAG_CORPUS` | RAG 사용 시 필수 | Vertex RAG corpus resource name |
| `VERTEX_RAG_LOCATION` | 현재는 사실상 미사용 | 설정 클래스에는 있으나 실제 RAG 호출에는 쓰이지 않음 |
| `FILESYSTEM_ALLOWED_DIR` | 선택 | Filesystem MCP 허용 디렉터리. 여러 개면 쉼표 구분 |
| `REASONING_ENGINE_APP_NAME` | 현재 코드에서 사용 | `Runner(app_name=...)`에 전달됨 |
| `REASONING_ENGINE_ID` | 현재 코드에서 사용 | `create_session(app_name=...)`에 전달됨 |

추가로 GCP 인증이 필요합니다. 일반적으로 아래 둘 중 하나를 맞춰야 합니다.

- `gcloud auth application-default login`
- `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json`

이 저장소에는 [secrets/gcp_account_credentials.json](/home/pachu/works/adk-project-final/secrets/gcp_account_credentials.json) 파일이 있지만, 실제 사용 여부는 셸 환경과 `.env` 설정에 따라 달라집니다.

## Agent Engine 생성

Agent Engine 리소스를 한 번 생성하려면 아래 스크립트를 실행합니다.

```bash
python3 scripts/create_agent_engine.py
```

스크립트 위치: [scripts/create_agent_engine.py](/home/pachu/works/adk-project-final/scripts/create_agent_engine.py)

이 스크립트는 다음을 수행합니다.

- `.env`에서 `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`을 읽음
- `vertexai.Client(...)`를 생성
- `client.agent_engines.create()` 실행
- 생성된 리소스 이름을 출력

출력된 값은 최소한 `.env`의 `REASONING_ENGINE_APP_NAME`에 반영해야 합니다.

현재 코드상 `REASONING_ENGINE_ID`도 별도로 읽고 있으므로, 실제 배포/세션 생성에 필요한 값이 무엇인지 사용 환경에 맞게 함께 맞춰야 합니다.

## 실행

CLI 실행:

```bash
python3 main.py
```

현재 `main.py`는 내부적으로 [app/services/chat_cli.py](/home/pachu/works/adk-project-final/app/services/chat_cli.py)를 호출해 아래 순서로 동작합니다.

1. `.env` 설정 로드
2. `vertexai.init(...)`
3. `VertexAiSessionService(...)` 생성
4. `Runner(...)` 생성
5. 세션 생성
6. 터미널 입력을 받아 ADK runner로 전달
7. 함수 호출과 함수 응답을 디버그 로그로 출력
8. 최종 응답 텍스트 출력

종료 명령:

```text
exit
quit
```

## 에이전트 구조

### Root Agent

[app/agent/root.py](/home/pachu/works/adk-project-final/app/agent/root.py)

- `SupervisorAgent` 하나를 루트 에이전트로 사용
- 모델은 `settings.model`
- 아래 workflow를 tool로 등록
  - `run_sequential_docu_summary_pipeline`
  - `run_parallel_tech_compare_pipeline`
  - `run_sequential_rag_pipeline`

### Workflows

[app/agent/workflows.py](/home/pachu/works/adk-project-final/app/agent/workflows.py)

- `run_parallel_tech_compare_pipeline()`

 
- `run_sequential_docu_summary_pipeline()`
  
- `run_sequential_rag_pipeline()`
  


### Sub Agents

[app/agent/sub_agents.py](/home/pachu/works/adk-project-final/app/agent/sub_agents.py)

- `make_ragengine_search_agent()`
  - `search_vertex_rag` 함수 툴을 사용
  - Vertex RAG corpus 검색 수행
- `make_merge_agent()`
  - 결과 병합용
- `make_save_to_file_agent()`
  - Filesystem MCP를 이용한 파일 저장용
- `make_summary_only_agent()`
  - 요약 응답용

현재 workflow 연결 상태를 보면, 이 중 일부는 정의만 되어 있고 기본 실행 경로에 연결되지는 않았습니다.

## RAG 검색 방식

`search_vertex_rag(query: str)`는 `google.genai.Client(vertexai=True, ...)`를 사용해 `generate_content(...)` 호출 안에 retrieval tool을 붙이는 방식입니다.

설정 포인트:

- corpus: `VERTEX_RAG_CORPUS`
- top-k: `5`
- vector distance threshold: `0.3`
- ranking model: `semantic-ranker-512`

RAG 검색에 필요한 값이 비어 있으면 문자열 에러 메시지를 반환하도록 되어 있습니다.

## MCP Filesystem

[app/mcp/toolsets.py](/home/pachu/works/adk-project-final/app/mcp/toolsets.py)

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

[app/services/runtime_logging.py](/home/pachu/works/adk-project-final/app/services/runtime_logging.py)와 [app/tool/callbacks.py](/home/pachu/works/adk-project-final/app/tool/callbacks.py)에서 tool call 직전 로그를 출력합니다.

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

- [main.py](/home/pachu/works/adk-project-final/main.py)
- [agent.py](/home/pachu/works/adk-project-final/agent.py)
- [app/config/settings.py](/home/pachu/works/adk-project-final/app/config/settings.py)
- [app/services/chat_cli.py](/home/pachu/works/adk-project-final/app/services/chat_cli.py)
- [app/agent/root.py](/home/pachu/works/adk-project-final/app/agent/root.py)
- [app/agent/workflows.py](/home/pachu/works/adk-project-final/app/agent/workflows.py)
- [app/agent/sub_agents.py](/home/pachu/works/adk-project-final/app/agent/sub_agents.py)
- [app/mcp/toolsets.py](/home/pachu/works/adk-project-final/app/mcp/toolsets.py)
- [app/prompt/instructions.py](/home/pachu/works/adk-project-final/app/prompt/instructions.py)
- [scripts/create_agent_engine.py](/home/pachu/works/adk-project-final/scripts/create_agent_engine.py)



