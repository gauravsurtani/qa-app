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

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

# Invoke uvicorn directly from the prod venv. Avoids `uv run` re-syncing dev deps
# at container start, which was timing out the healthcheck. $PORT is set by Railway.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
