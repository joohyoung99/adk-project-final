from __future__ import annotations


import vertexai

from app.config.settings import settings



##vertexaisession 사용 위한 reasoningengine 도출용 
def main() -> None:
    """Vertex AI Agent Engine을 생성하고 리소스 이름을 출력한다."""

    vertexai.init(
        project=settings.google_cloud_project,
        location= settings.google_cloud_location,
    )

    client = vertexai.Client(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
    agent_engine = client.agent_engines.create()
    resource_name = agent_engine.api_resource.name

    print("Agent Engine created.")
    print(resource_name)
    print("")
    print("Put this in your .env:")
    print(f"REASONING_ENGINE_ID={resource_name}")


if __name__ == "__main__":
    main()
