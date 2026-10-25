# Build with repository-root context: docker build -f apps/api/Dockerfile .
FROM python:3.11-slim AS native
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /source
COPY native/pokerth ./native/pokerth
COPY scripts/build_pokerth.py ./scripts/build_pokerth.py
RUN python3 scripts/build_pokerth.py

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/wtr ./wtr
COPY --from=native /source /opt/source
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 POKERTH_BINARY="/opt/source/native/pokerth/build/pokerth-opponent"
EXPOSE 8000
CMD ["uvicorn", "wtr.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
