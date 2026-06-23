# Kredit Lab OCR Service

Railway-deployed OCR API for the dashboard.

## Runtime

- Primary OCR: Azure Document Intelligence with `OCR_MODEL=azure-di`
- Backup OCR: LLM Whisperer when `LLMWHISPERER_API_KEY` is set
- Endpoint: `POST /parse` with multipart `file=<pdf>`
- Response shape: `{ chunks, parsed_pages_count, served_by }`
- Auth: `Authorization: Bearer <SERVICE_API_KEY>` when `SERVICE_API_KEY` is set

## Railway Variables

Set these on the OCR service:

```bash
SERVICE_API_KEY=...
OCR_MODEL=azure-di
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
LLMWHISPERER_API_KEY=...
OCR_GPU_MEMORY_IN_GB=32
OVIS_MEMORY_IN_GB=24
TENSORLAKE_MIN_CONTAINERS=0
USE_AZURE_OPENAI=false
AWS_REGION=us-east-1
```

`LLMWHISPERER_API_KEY` can stay blank if you want Azure-only OCR. The dashboard
does not need the Azure or LLM Whisperer secrets. It only needs the same
`SERVICE_API_KEY`.

## Dashboard URL

On Railway, the dashboard defaults to:

```text
http://kreditlab-ocr-service.railway.internal
```

Set dashboard `OCR_SERVICE_URL` only if the OCR service name is not
`kreditlab-ocr-service` or you want to call a public URL.

## Local Run

```bash
pip install -r service/requirements.txt
pip install -e . --no-deps
python -m service.app
```

Then call:

```bash
curl -X POST http://localhost:8000/parse \
  -H "Authorization: Bearer $SERVICE_API_KEY" \
  -F "file=@statement.pdf"
```
