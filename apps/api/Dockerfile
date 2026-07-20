FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

RUN python -m pip install --upgrade pip && python -m pip install .

EXPOSE 8000

CMD ["uvicorn", "--app-dir", "src", "codepilot_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
