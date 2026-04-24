# Upload -> OCR -> Enrich -> Graph -> Embeddings

This backend now runs a full ingestion pipeline when frontend uploads a file to:

`POST /api/v1/ingest/documents`

## Pipeline Flow

1. Save uploaded file locally with generated `document_id` (`doc_<hash>_<uuid>`).
2. For PDFs: split file into 100-page chunks and send each chunk to Mistral OCR.
3. Build:
   - `ocr_response_combined.json` (raw merged chunk output)
   - `ocr_response_combined_fixed.json` (same format with globally fixed page indices)
4. Run your existing scripts exactly:
   - `final_json.py` using `ocr_response_combined_fixed.json`
   - `graph_creation.py`
   - `embed_nodes.py`
5. Persist `output.json` exactly as produced by `final_json.py` and also mirror it to `enriched_document.json` for backward compatibility.
6. Tag graph nodes with `document_id` after graph creation.
7. Store processing metadata in local registry.

## Key Service Classes

- `app/services/mistral_ocr_service.py`
  - Handles Mistral file upload and chunked OCR merging.
- `app/services/job_pipeline_service.py`
  - Runs `final_json.py`, `graph_creation.py`, and `embed_nodes.py`.
- `app/services/ingest_service.py`
  - Orchestrates chunk OCR + script chain + artifact persistence.
- `app/services/graph_service.py`
  - Tags book subgraph with `document_id` and retrieval support.

## API Routes

- `POST /api/v1/ingest/documents` -> full ingestion pipeline
- `GET /api/v1/documents/list` -> list uploaded docs
- `DELETE /api/v1/documents/{doc_id}` -> remove doc graph + local files
- `POST /api/v1/query/search` -> retrieves from vector index and responds with sources

## Storage Layout

- `data/documents/<document_id>/`
  - original uploaded file
  - `ocr_response_combined.json`
  - `ocr_response_combined_fixed.json`
  - `output.json`
- `data/documents/registry.json`

## Required Environment Variables

- `MISTRAL_API_KEY`
- `MISTRAL_API_BASE` (default: `https://api.mistral.ai/v1`)
- `MISTRAL_OCR_MODEL` (default: `mistral-ocr-latest`)
- `MISTRAL_INCLUDE_IMAGE_BASE64` (default: `false`)
- `MISTRAL_DELETE_REMOTE_FILE` (default: `true`)
- `MISTRAL_OCR_CHUNK_SIZE_PAGES` (default: `100`)
- `MISTRAL_API_TIMEOUT_SECONDS` (default: `300`)
- `USE_JOB_AUTOMATION_PIPELINE` (default: `true`)
- `JOB_AUTOMATION_DIR` (default: `C:\Users\Admin\Downloads\job_automation`)
- `JOB_SCRIPT_TIMEOUT_SECONDS` (default: `7200`)
- `JOB_PYTHON_EXECUTABLE` (optional override)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `EMBEDDING_MODEL` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `EMBEDDING_DIM`, `EMBEDDING_BATCH_SIZE`
- `OLLAMA_BASE_URL` or `NGROK_URL` (for remote Ollama embeddings)
- `OLLAMA_EMBED_MODEL` (default: `nomic-embed-text-v2-moe`)
- `OLLAMA_TIMEOUT_SECONDS`
- `DATA_DIR` (default: `data`)
