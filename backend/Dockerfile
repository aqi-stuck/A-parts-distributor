FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PARTS_DB_PATH=/var/lib/parts-search/app.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ml ./ml
COPY config ./config
COPY data/catalog.json ./data/catalog.json

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /var/lib/parts-search \
    && chown appuser:appuser /var/lib/parts-search

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
