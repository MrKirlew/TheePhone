# Lightweight Python base
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy all Python files and requirements
COPY . .

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && pip install -r requirements.txt

# Cloud Run will set PORT
ENV PORT=8080

CMD ["python", "main_simple.py"]