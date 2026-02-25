FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY pm_bot ./pm_bot

RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir uvicorn

EXPOSE 8000

CMD ["uvicorn", "pm_bot.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
