from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")



def _filesystem_allowed_dirs() -> list[str]:
    """환경 변수에서 Filesystem MCP 허용 디렉터리 목록을 읽는다."""
    raw = (os.getenv("FILESYSTEM_ALLOWED_DIR") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [str(BASE_DIR / "allowed_dir")]


@dataclass(frozen=True, slots=True)
class Settings:
    """애플리케이션 전역 설정을 .env 기반으로 보관한다."""
    user_id: str = str(uuid.uuid4())
    model: str = os.getenv("MODEL_GEMINI_2_5_FLASH", "gemini-2.5-flash")
    filesystem_allowed_dirs: list[str] = None  # type: ignore[assignment]
    vertex_rag_location: str = os.getenv("VERTEX_RAG_LOCATION", "asia-northeast3")
    vertex_rag_corpus: str = os.getenv("VERTEX_RAG_CORPUS", "projects/854975691211/locations/asia-northeast3/ragCorpora/2017612633061982208") #TODO: 변경 할것
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    google_agent_engine_name: str = os.getenv("REASONING_ENGINE_APP_NAME","")
    google_agent_engine: str = os.getenv("REASONING_ENGINE_ID","")

    def __post_init__(self) -> None:
        """후처리로 파생 설정값을 채운다."""
        object.__setattr__(self, "filesystem_allowed_dirs", _filesystem_allowed_dirs())


    @property
    def filesystem_allowed_dir(self) -> str:
        """대표 허용 디렉터리 하나를 반환한다."""
        return self.filesystem_allowed_dirs[0]


settings = Settings()
