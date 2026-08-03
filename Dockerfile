FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY clearslate/ clearslate/
RUN uv sync --locked --no-dev
COPY --from=ui /ui/dist frontend/dist
ENV PORT=8080
CMD ["uv", "run", "--no-sync", "uvicorn", "clearslate.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
