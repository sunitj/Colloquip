# Stage 1: Python dependencies
FROM python:3.11-slim AS python-deps

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project --extra api --extra db --extra db-pg --extra llm --extra embeddings

# Stage 2: Frontend build
FROM node:20-slim AS frontend-build

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run build

# Stage 3: Production image
FROM python:3.11-slim AS production

RUN groupadd -r colloquip && useradd -r -g colloquip -d /app colloquip

WORKDIR /app

# Copy Python deps from stage 1
COPY --from=python-deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY src/ ./src/
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy frontend build from stage 2
COPY --from=frontend-build /web/dist ./static/

# Make source importable
ENV PYTHONPATH="/app/src"

# Switch to non-root user
USER colloquip

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "colloquip.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
