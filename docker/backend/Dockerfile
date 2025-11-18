FROM python:3.11-slim-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        curl \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY scripts scripts

RUN python scripts/install_pytorch.py --force-cpu --pip-retries 3 --pip-retry-delay 5

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

ENV VISUAL_SEARCH_CATALOG_DIR=/app/data/catalog \
    VISUAL_SEARCH_INDEX_BASE_PATH=/app/data/catalog_index \
    PYTHONPATH=/app

COPY docker/backend/entrypoint.sh docker/backend/entrypoint.sh
RUN chmod +x docker/backend/entrypoint.sh

USER appuser

ENTRYPOINT ["./docker/backend/entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
