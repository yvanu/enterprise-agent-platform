FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN pip install --no-cache-dir ".[postgres]" \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic -c alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
