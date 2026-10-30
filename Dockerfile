# Two stages: Node builds the React UI, then a slim Python image runs FastAPI,
# which serves both the API and the built UI on port 8000.

# ---- Stage 1: build the frontend (not shipped; only dist/ is copied out) ----
FROM node:24-alpine AS frontend
WORKDIR /app/frontend
# Copy the dependency files first so `npm ci` is cached until they change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: run the backend ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# Pick up security fixes released since the base image was published. The IDE's CVE count is for the
# published tag; what's left after this upgrade has no fix in Debian yet.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY backend/ ./
# main.py looks for the UI at ../frontend/dist, so keep the same layout.
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Run as an unprivileged user.
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
# Migrate, load templates/skills, then start the server.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
