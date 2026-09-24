FROM --platform=linux/arm64 python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml uv.lock* ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY . .

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
