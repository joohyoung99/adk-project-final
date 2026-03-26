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




추가로 GCP 인증이 필요합니다. 일반적으로 아래 둘 중 하나를 맞춰야 합니다.

- `gcloud auth application-default login`
- `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json`



## 실행

CLI 실행:

```bash
python3 main.py
```


## 에이전트 구조

### Root Agent

[app/agent/root.py]

- `SupervisorAgent` 하나를 루트 에이전트로 사용
- 모델은 `settings.model`
- 아래 workflow를 tool로 등록
  - `run_sequential_docu_summary_pipeline`
  - `run_parallel_tech_compare_pipeline`
  - `run_sequential_rag_pipeline`

### Workflows

[app/agent/workflows.py]

- `run_parallel_tech_compare_pipeline()`

 
- `run_sequential_docu_summary_pipeline()`
  
- `run_sequential_rag_pipeline()`
  


### Sub Agents

[app/agent/sub_agents.py]



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



