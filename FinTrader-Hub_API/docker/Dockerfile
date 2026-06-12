FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 fintrader \
    && useradd --uid 1000 --gid fintrader --create-home fintrader

COPY --from=builder /install /usr/local

# Application source. Secrets are excluded via .dockerignore (.env never in build context).
COPY . .

# Fail-fast: refuse image build if secrets were accidentally copied into layers.
RUN test ! -e /app/.env \
    && test ! -e /app/.env.local \
    && test ! -e /app/.env.production \
    && test ! -e /app/.env.development

RUN chown -R fintrader:fintrader /app

USER fintrader

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
