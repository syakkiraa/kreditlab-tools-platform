# Root-context Railway Dockerfile.
#
# Railway builds from the repository root unless the service Root Directory is
# set to "dashboard". This file mirrors dashboard/Dockerfile but uses
# root-relative COPY paths so the monorepo root is also deployable.
FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip \
      libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
      libcairo2 libgdk-pixbuf-2.0-0 libffi8 \
      fontconfig fonts-inter fonts-liberation fonts-dejavu-core \
      fonts-symbola shared-mime-info poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY dashboard/docker/fonts/NotoColorEmoji.ttf /usr/local/share/fonts/NotoColorEmoji.ttf
COPY dashboard/docker/fonts/99-color-emoji.conf /etc/fonts/conf.d/99-color-emoji.conf
RUN fc-cache -fv

WORKDIR /app

COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --include=dev

COPY dashboard/financial-statement-analysis-logic/requirements.txt financial-statement-analysis-logic/requirements.txt
COPY dashboard/bank-statement-analysis-logic/requirements.txt bank-statement-analysis-logic/requirements.txt
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r financial-statement-analysis-logic/requirements.txt \
 && /opt/venv/bin/pip install --no-cache-dir -r bank-statement-analysis-logic/requirements.txt

COPY dashboard/. .

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

ENV NODE_ENV=production \
    FINANCIAL_RENDERER_PYTHON_BIN=/opt/venv/bin/python \
    BANK_STATEMENT_ANALYZER_PYTHON_BIN=/opt/venv/bin/python

EXPOSE 3000
CMD ["npm", "run", "start"]
