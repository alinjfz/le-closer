# syntax=docker/dockerfile:1
# Le Closer — single lightweight image: backend (FastAPI) + built frontend + Meet bot.
# Layer order is chosen for fast rebuilds: heavy deps are cached, code is copied last.

# ---- Stage 1: build the frontend (node, discarded) ----
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS backend-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    LECLOSER_BACKEND=http://localhost:8003

WORKDIR /app

# Minimal system libs for chromium-headless-shell (cached layer — changes only
# if the browser requirements change, NOT when app code changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libx11-6 \
      libxcb1 libxext6 libexpat1 libglib2.0-0 libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps (cached layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App user + browser dir (tiny layer), then browser download AS the app user
# so no chown/chmod copy layer is created
RUN useradd -m -u 1000 lecloser && mkdir -p /ms-playwright /home/lecloser/.config/lecloser && chown -R lecloser:lecloser /ms-playwright /home/lecloser/.config
USER lecloser
RUN playwright install chromium-headless-shell

# Development runs source bind mounts with Uvicorn's reloader.
FROM backend-base AS development
EXPOSE 8003
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload", "--reload-dir", "/app/backend", "--reload-dir", "/app/bot", "--timeout-graceful-shutdown", "5"]

FROM backend-base AS runtime
# App code — copied last so code changes don't invalidate the layers above
COPY --chown=lecloser:lecloser backend/ ./backend/
COPY --chown=lecloser:lecloser bot/ ./bot/
COPY --from=frontend-build --chown=lecloser:lecloser /build/dist ./frontend/dist

EXPOSE 8003
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

# Default: backend + dashboard on :8003. Run the bot with:
#   docker run <img> python -m bot.run --demo --create-call
#   docker run <img> python -m bot.run --meet-url https://meet.google.com/xxx --call-id <id>
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
