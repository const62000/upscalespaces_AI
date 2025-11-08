FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt


# ==============================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    REDIS_URL=redis://localhost:6379/0 \
    C_FORCE_ROOT=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server supervisor && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder /install /usr/local

COPY . .

RUN useradd --no-create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 80

RUN mkdir -p /etc/supervisor/conf.d
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Health check to verify Redis
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s \
  CMD redis-cli ping | grep -q PONG || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
