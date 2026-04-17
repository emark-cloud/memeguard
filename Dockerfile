# FourScout backend — self-hosted single-tenant deployment.
# Runs the FastAPI app plus the Four.meme CLI subprocess it depends on.
# See FourScout.md §18 for the non-custodial multi-tenant roadmap.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_MAJOR=20

# Node.js (for the Four.meme CLI subprocess) + curl for the NodeSource bootstrap.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the Four.meme CLI into /app/fourmeme-cli/node_modules/.bin/fourmeme,
# matching the path backend/clients/fourmeme_cli.py resolves at runtime.
RUN mkdir -p /app/fourmeme-cli \
 && cd /app/fourmeme-cli \
 && npm init -y >/dev/null \
 && npm install --omit=dev @four-meme/four-meme-ai@^1.0.8

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

# SQLite DB mounts here. Volume in docker-compose.yml preserves it across rebuilds.
RUN mkdir -p /app/data
ENV DATABASE_PATH=/app/data/fourscout.db

EXPOSE 8000

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
