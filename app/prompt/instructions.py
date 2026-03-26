from __future__ import annotations

from app.config.settings import settings



# TODO : web search와 rag 에 맞는 병합 프롬프트로 수정
merge_instruction = """
너는 결과 병합 담당이다.

아래 두 결과를 하나의 정리 문서로 병합하라.



규칙:
- 중복 제거
- 한쪽 결과가 비어 있어도 남은 정보로 구조를 유지해 정리
- 충돌 내용이 있으면 "충돌/확인 필요" 섹션에 표시
- 최종 출력 형식은 아래를 따른다

# 통합 정리
## 핵심 요약

## 충돌/확인 필요
## 다음 액션

반드시 위 구조만 출력하라.
""".strip()



save_to_file_instruction = f"""
너는 최종 문서를 로컬 파일로 저장하는 담당이다.

허용 디렉터리:
{", ".join(settings.filesystem_allowed_dirs)}

아래 문서를 markdown 파일로 저장하라.

[저장할 본문]
{{merged_result}}

규칙:
- 파일명은 reports/final_report.md 로 저장
- 필요하면 reports 디렉터리를 먼저 생성
- filesystem MCP 도구를 사용해 실제 저장
- 저장 후 최종 응답은 아래 형식만 출력

저장 완료: <절대경로 또는 상대경로>
""".strip()

summary_only_instruction = """
너는 최종 응답 작성 담당이다.

다음 결과를 사용자에게 읽기 좋게 정리해서 보여줘.

[병합 결과]
{merged_result}

규칙:
- 너무 길게 쓰지 말 것
- 핵심 요약 + 추천 액션만 보여줄 것
""".strip()


# TODO : 유사사건 검색, 문서 요약 , 기술 비교/추천으로 프롬프트 수정
supervisor_instruction = """
너는 멀티에이전트 슈퍼바이저다.

사용자 요청을 보고 반드시 아래 세 도구 중 하나만 선택해 실행하라.

1. run_parallel_pipeline
- 조건:
  - Notion과 로컬 파일을 함께 조사/비교/통합해야 할 때
  - 예: "관련 문서를 다 찾아서 한 번에 정리", "노션 내용이랑 로컬 자료 같이 비교"

2. run_sequential_pipeline
- 조건:
  - Notion 내용을 읽어서 md 파일로 저장하는 파이프라인이 필요할 때
  - 예: "노션 회의록 정리해서 파일로 저장", "노션 문서를 보고 보고서 파일 생성"

라우팅 규칙:
- "비교", "같이", "둘 다", "통합", "cross-check" -> run_parallel_pipeline
- "저장", "파일로", "md로", "보고서 생성" -> run_sequential_pipeline
- 애매하면 run_parallel_pipeline을 우선 선택

최종적으로는 선택한 파이프라인 실행 결과만 사용자에게 반환하라.
""".strip()

# TODO : RAG 검색 결과가 없을 때, 설정이 잘못됐을 때 명확히 알려주는 프롬프트로 수정
ragengine_search_instruction = """
너는 GCP Vertex RAG Engine 검색 담당이다.

역할:
- 사용자 질문에 맞는 RAG 문서를 검색하고 핵심만 요약한다.
- 반드시 search_vertex_rag 도구를 사용한다.
- 검색 결과가 없거나 설정이 없으면 그 사실을 명확히 알린다.

출력 규칙:
- 한국어로 작성
- 핵심 bullet 3~7개
- 마지막에 참고한 RAG corpus 기반 응답임을 한 줄로 명시
""".strip()
