# Kredit Lab OCR service: Azure Document Intelligence + LLM Whisperer fallback.
FROM python:3.12-slim

# Native deps used by the vendored Azure markdown extractor.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the vendored OCR helpers without pulling the remote workflow SDK.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e . --no-deps

# Service deps
COPY service/requirements.txt ./service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt

COPY service ./service

# Railway injects $PORT at runtime; app.py reads it directly.
ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "service.app"]
