FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libglib2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-inter \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    fonts-symbola \
    fontconfig \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
