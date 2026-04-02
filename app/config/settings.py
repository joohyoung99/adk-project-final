from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")




@dataclass(frozen=True, slots=True)
class Settings:
    """애플리케이션 전역 설정을 .env 기반으로 보관한다."""
    user_id: str = str(uuid.uuid4())
    model: str = os.getenv("MODEL_GEMINI_2_5_FLASH", "gemini-2.5-flash")
    vertex_rag_location: str = os.getenv("VERTEX_RAG_LOCATION", "asia-northeast3")
    vertex_rag_corpus: str = os.getenv("VERTEX_RAG_CORPUS","") 
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    reasoning_engine_location: str = os.getenv("REASONING_ENGINE_LOCATION",os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    google_agent_engine_name: str = os.getenv("REASONING_ENGINE_APP_NAME","")
    google_agent_engine: str = os.getenv("REASONING_ENGINE_ID","")
    github_mcp_server_path: str = os.getenv("GITHUB_MCP_SERVER_PATH", "")
    github_personal_access_token: str = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    discovery_engine_location: str = os.getenv("DISCOVERY_ENGINE_LOCATION", "global")
    discovery_engine_engine_id: str = os.getenv("DISCOVERY_ENGINE_ENGINE_ID", "")




settings = Settings()
