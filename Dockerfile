FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app
# Disable development dependencies
ENV UV_NO_DEV=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "main:app"]
