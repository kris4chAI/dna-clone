# FlyHigh Navigator: one image with the React UI, the FastAPI API, the skills and the assets.
# Base images can be swapped for a corporate mirror: docker compose build --build-arg PYTHON_IMAGE=... --build-arg NODE_IMAGE=...
ARG NODE_IMAGE=node:20-slim
ARG PYTHON_IMAGE=python:3.12-slim

# ---------- 1. Build the UI ----------
FROM ${NODE_IMAGE} AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 2. Runtime ----------
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLYHIGH_HOME=/srv FLYHIGH_DATA=/srv/data PORT=8000
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --prefer-binary -r backend/requirements.txt
COPY backend/ backend/
COPY skills/ skills/
COPY assets/ assets/
COPY docker/entrypoint.sh /usr/local/bin/flyhigh-entrypoint
COPY --from=ui /ui/dist frontend/dist
RUN chmod +x /usr/local/bin/flyhigh-entrypoint \
 && useradd --create-home --uid 10001 flyhigh \
 && mkdir -p /srv/secrets /srv/data && chown -R flyhigh:flyhigh /srv
USER flyhigh
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
ENTRYPOINT ["flyhigh-entrypoint"]
