# Visual Search

Find visually similar catalog items by uploading an image. The backend extracts CLIP ViT-B/32 embeddings with PyTorch/OpenCLIP, normalizes them, and performs cosine search with FAISS. The React frontend provides drag‑and‑drop upload, backend readiness checks, and similarity visualizations.

## Architecture
- **Backend** (`backend/`): FastAPI, PyTorch, OpenCLIP, OpenCV, FAISS. `feature_extractor.py` wraps CLIP, `similarity_search.py` manages the FAISS index on disk (`data/catalog_index.*`), and `main.py` exposes the API plus static catalog assets under `/data`.
- **Frontend** (`frontend/`): React 18 single-page app with components such as `ImageUpload` and `SearchResults` in `src/components/`.
- **Scripts** (`scripts/`):
  - `run.bat` / `run.sh` bootstrap uv, create a Python 3.11 virtualenv, install dependencies, call `scripts/install_pytorch.py`, ensure `data/catalog/`, and launch backend/frontend dev servers.
  - `scripts/install_pytorch.py` inspects `nvidia-smi` and installs the right PyTorch + Torchvision wheel (CUDA 11.8 when available, CPU otherwise) and OpenCLIP, with `--force-cpu`, `--pip-retries`, and `--pip-retry-delay` flags for flaky environments.
  - `scripts/download_pass_catalog.py` downloads random samples from the PASS dataset (parallelized) into `data/catalog/`, now with shared retry logic and a `--dry-run` preview mode.

## Prerequisites
- Python 3.8–3.11 (3.11 recommended). On Windows install Python 3.11 with the `py` launcher and run the scripts from a shell *without* an active virtualenv.
- [`uv`](https://docs.astral.sh/uv/) CLI.
- Node.js 16+.
- Optional: `nvidia-smi` (GPU acceleration). The backend works on CPU if CUDA is absent.

## Quick Start
### Automated (recommended)
```powershell
# Windows
run.bat
```
```bash
# macOS / Linux / WSL
chmod +x run.sh
./run.sh
```
The script selects a compatible Python interpreter, recreates `venv/` if needed, installs backend dependencies via `uv`, runs the PyTorch installer (CUDA-aware), ensures `data/catalog/` exists, installs frontend deps on first run, and starts uvicorn + `npm start`.

### Manual Workflow
```bash
# Backend
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
uv pip install --python "$VIRTUAL_ENV/bin/python" -r requirements.txt
python scripts/install_pytorch.py  # add --force-cpu or tweak --pip-retries/--pip-retry-delay for flaky installs
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm start
```

## Features

- Visual similarity search with drag-and-drop upload
- Catalog browser with pageable grid (up to 200 images per page), modal previews, uploads, and deletes
- CLIP ViT-B/32 embeddings (OpenCLIP) + FAISS cosine similarity with configurable minimum confidence
- Query-time augmentations (flip + crop) for robust matches
- GPU acceleration (CUDA/DirectML/MPS) with automatic fallback to CPU
- Modern React frontend with live status feedback
- REST API with interactive docs (`/docs`)

## Catalog Data (PASS)
Populate `data/catalog/` with public imagery:
```bash
python scripts/download_pass_catalog.py --count 1000 --seed 123
```
Flags:
- `--workers` (default 8) controls parallel downloads.
- `--urls` can point to a locally mirrored `pass_urls.txt`.
- `--insecure` skips TLS validation (for corporate proxies).
- `--dry-run` prints the planned download list without fetching files.
- `--retry-attempts` / `--retry-delay` control the backoff used for fetching the URL list and per-image downloads.

On startup the backend checks whether `data/catalog_index.*` matches the current files; it rebuilds the FAISS cache automatically if files changed, were removed, or the embedding dimension differs.

## Configuration
All important knobs live in `backend/config.py` (`AppConfig`). Override anything via `.env` or `VISUAL_SEARCH_*` variables. Every setting is validated at startup so invalid values fail fast instead of causing runtime surprises.

### Key Settings

| Setting | Env Var | Default | Notes |
| --- | --- | --- | --- |
| `catalog_dir` | `VISUAL_SEARCH_CATALOG_DIR` | `data/catalog` | Directory where catalog imagery is stored. |
| `index_base_path` | `VISUAL_SEARCH_INDEX_BASE_PATH` | `data/catalog_index` | Base path for FAISS cache files (creates `.index` + `.pkl`). |
| `index_build_batch_size` | `VISUAL_SEARCH_INDEX_BUILD_BATCH_SIZE` | `32` | Min `1`. Batch size for feature extraction when rebuilding the index. |
| `index_build_workers` | `VISUAL_SEARCH_INDEX_BUILD_WORKERS` | `4` | Min `1`. Thread pool size for catalog ingestion. |
| `cache_index_on_startup` | `VISUAL_SEARCH_CACHE_INDEX_ON_STARTUP` | `true` | If `true`, saves FAISS cache after building to speed future startups. |
| `catalog_default_page_size` | `VISUAL_SEARCH_CATALOG_DEFAULT_PAGE_SIZE` | `40` | Min `1`. Default page size for the catalog browser. |
| `catalog_max_page_size` | `VISUAL_SEARCH_CATALOG_MAX_PAGE_SIZE` | `200` | Must be ≥ default. Hard limit for catalog pagination. |
| `feature_model_name` | `VISUAL_SEARCH_FEATURE_MODEL_NAME` | `ViT-B-32` | CLIP/OpenCLIP backbone. |
| `feature_model_pretrained` | `VISUAL_SEARCH_FEATURE_MODEL_PRETRAINED` | `openai` | Weights identifier passed to OpenCLIP. |
| `query_use_horizontal_flip` | `VISUAL_SEARCH_QUERY_USE_HORIZONTAL_FLIP` | `true` | Adds flipped variant during search. |
| `query_use_center_crop` | `VISUAL_SEARCH_QUERY_USE_CENTER_CROP` | `true` | Adds cropped variant during search. |
| `query_crop_ratio` | `VISUAL_SEARCH_QUERY_CROP_RATIO` | `0.9` | Must be `0 < ratio ≤ 1`. Size of the retained crop. |
| `search_default_top_k` | `VISUAL_SEARCH_SEARCH_DEFAULT_TOP_K` | `200` | Min `1`. Used when clients omit `top_k`. |
| `search_max_top_k` | `VISUAL_SEARCH_SEARCH_MAX_TOP_K` | `1000` | Must be ≥ default. Guards against unbounded searches. |
| `search_min_similarity` | `VISUAL_SEARCH_SEARCH_MIN_SIMILARITY` | `0.8` | Must be between `0` and `1`. Minimum cosine similarity. |
| `search_results_page_size` | `VISUAL_SEARCH_SEARCH_RESULTS_PAGE_SIZE` | `10` | Min `1`. Frontend page size for query results. |
| `supported_image_formats` | `VISUAL_SEARCH_SUPPORTED_IMAGE_FORMATS` | `.jpg,.jpeg,.jfif,.png,.gif,.bmp,.tiff,.tif,.webp` | Comma-separated extensions, automatically normalized to lowercase with leading dots. |

You can override any value by exporting the environment variable or adding it to `.env`:

```powershell
set VISUAL_SEARCH_SEARCH_MAX_TOP_K=50
set VISUAL_SEARCH_CATALOG_DIR=D:\datasets\catalog
```

```
# .env
VISUAL_SEARCH_FEATURE_MODEL_NAME=ViT-H-14
VISUAL_SEARCH_INDEX_BUILD_WORKERS=8
VISUAL_SEARCH_CATALOG_MAX_PAGE_SIZE=150
```

If a provided value breaks the documented constraints (e.g., `VISUAL_SEARCH_SEARCH_MIN_SIMILARITY=1.5` or `VISUAL_SEARCH_CATALOG_MAX_PAGE_SIZE` lower than the default), the backend fails fast during startup with a clear validation error so you can fix configuration issues immediately.

## API & UI Endpoints
- Frontend SPA: http://localhost:3000
- REST API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Key routes:
  - `POST /search` – run similarity search (returns all matches ≥ configured confidence)
  - `POST /add-product` – upload a new catalog image (used by the catalog browser)
  - `GET /catalog/items` – paginated catalog listing (`page`, `page_size≤200`)
  - `DELETE /catalog/{product_id}` – remove a catalog entry (index rebuilds automatically)
- `GET /catalog` - legacy full catalog dump (unchanged)
- `GET /stats` - frontend boot metadata (page sizes, supported formats, etc.)

### Response Details

- `POST /search` returns a JSON array of `SearchResult` objects (`product` + `similarity_score`) and emits an `X-Total-Matches` response header indicating how many catalog entries met the requested `min_similarity`. Clients can use that header to show aggregate result counts without fetching another page.

- `POST /add-product` and `DELETE /catalog/{product_id}` both respond with `{ "message": "...", "product_id": "..." }` payloads so the UI can attribute toast/alert text to a specific catalog entry.

- `GET /stats` returns the current backend configuration snapshot:

```json
{
  "total_products": 128,
  "model": "ViT-B-32",
  "feature_dim": 512,
  "search_max_top_k": 1000,
  "search_min_similarity": 0.8,
  "results_page_size": 10,
  "supported_formats": [".jpg", ".png", "..."],
  "catalog_default_page_size": 40,
  "catalog_max_page_size": 200
}
```

- **Catalog Browser**:
  - Switch to the "Catalog Browser" tab in the UI to list every catalog entry.
  - Adjust page size (up to 200), paginate through pages, preview in a modal, upload new assets, or delete unwanted items.
  - Uploads are cached immediately; deletions trigger an automatic FAISS rebuild so search results stay consistent.

## GPU Acceleration
`scripts/install_pytorch.py` prefers CUDA 11.8 wheels when `nvidia-smi` exists; otherwise it installs CPU wheels. At runtime `backend/gpu_utils.py` logs the detected accelerator (CUDA, MPS, or CPU). No TensorFlow/DirectML code remains.

## Troubleshooting
- **Python version errors**: ensure `py -3.11` (Windows) or `python3.11` (Unix) is installed; PyTorch wheels are only available for 3.8–3.11.
- **Missing frontend assets**: delete `frontend/node_modules` and rerun `npm install`.
- **Image 404s / duplicates**: confirm referenced files exist under `data/catalog/`. Use the catalog browser delete button to remove broken entries—the backend rebuilds FAISS automatically.
- **PyTorch install failures**: rerun `python scripts/install_pytorch.py --force-cpu` inside `venv` or follow https://pytorch.org/get-started/locally/ for custom CUDA builds.

## Contributing
Follow the service structure above, keep functions typed, prefer async in the frontend when calling Axios, and add Pytest / React Testing Library smoke tests alongside new features. Document any `.env` changes and avoid committing large binaries or proprietary datasets.
