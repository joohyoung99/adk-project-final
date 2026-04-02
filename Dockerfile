# --- UI 빌드 스테이지 ---
FROM node:20-alpine AS ui-builder

WORKDIR /ui

COPY ui/package.json ./
RUN npm install
COPY ui /ui
RUN npm run build

# --- Python 빌드 스테이지 ---
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . /app

# --- 실행 스테이지 ---
FROM python:3.13-slim-bookworm AS runtime

COPY --from=builder /app /app
COPY --from=ui-builder /ui/dist /app/ui/dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app

EXPOSE 8080

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
