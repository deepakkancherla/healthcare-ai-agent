FROM python:3.14-slim

LABEL org.opencontainers.image.title="Healthcare AI Agent" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --create-home \
        --shell /usr/sbin/nologin appuser

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000 8501

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
