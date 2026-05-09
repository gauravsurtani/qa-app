FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY static ./static
COPY templates ./templates

EXPOSE 8000

# Use shell form so $PORT (set by Railway) expands. Fallback to 8000 for local docker.
CMD uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
