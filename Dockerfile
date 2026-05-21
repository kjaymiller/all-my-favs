FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
 && pip install \
      "fastapi>=0.115" "uvicorn[standard]>=0.32" \
      "sqlalchemy>=2.0" "psycopg[binary]>=3.2" \
      "alembic>=1.13" "pydantic-settings>=2.5" \
      "jinja2>=3.1" "python-multipart>=0.0.12" "httpx>=0.27"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Install the project itself (no deps — deps are pinned above) so
# `importlib.metadata.version("all-my-favs")` resolves at runtime.
RUN pip install --no-deps .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
