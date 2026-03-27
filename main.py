from __future__ import annotations

import asyncio

from app.services.chat_cli import run_chat_cli



def main() -> None:
    """CLI 채팅 루프를 비동기로 실행한다."""
    asyncio.run(run_chat_cli())


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(exc)
