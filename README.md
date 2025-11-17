# Visual Search

Find visually similar catalog items by uploading an image. The backend extracts CLIP ViT-B/32 embeddings with PyTorch/OpenCLIP, normalizes them, and performs cosine search with FAISS. The React frontend provides drag‑and‑drop upload, backend readiness checks, and similarity visualizations.

## Architecture
- **Backend** (`backend/`): FastAPI, PyTorch, OpenCLIP, OpenCV, FAISS. `feature_extractor.py` wraps CLIP, `similarity_search.py` manages the FAISS index on disk (`data/catalog_index.*`), and `main.py` exposes the API plus static catalog assets under `/data`.
- **Frontend** (`frontend/`): React 18 single-page app with components such as `ImageUpload` and `SearchResults` in `src/components/`.
- **Scripts** (`scripts/`):
  - `run.bat` / `run.sh` bootstrap uv, create a Python 3.11 virtualenv, install dependencies, call `scripts/install_pytorch.py`, ensure `data/catalog/`, and launch backend/frontend dev servers.
  - `scripts/install_pytorch.py` inspects `nvidia-smi` and installs the right PyTorch + Torchvision wheel (CUDA 11.8 when available, CPU otherwise) and OpenCLIP.
  - `scripts/download_pass_catalog.py` downloads random samples from the PASS dataset (parallelized) into `data/catalog/`.

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
python scripts/install_pytorch.py  # add --force-cpu to skip CUDA
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

On startup the backend checks whether `data/catalog_index.*` matches the current files; it rebuilds the FAISS cache automatically if files changed, were removed, or the embedding dimension differs.

## Configuration
All important knobs are centralized in `backend/config.py` (the `AppConfig` class). Key options:
- Catalog/index paths (`catalog_dir`, `index_base_path`), batch size, and worker counts for FAISS rebuilds plus catalog pagination limits (`catalog_default_page_size`, `catalog_max_page_size`).
- CLIP backbone selection (`feature_model_name`, `feature_model_pretrained`).
- Query augmentations (`query_use_horizontal_flip`, `query_use_center_crop`, `query_crop_ratio`).
- Search limits (`search_default_top_k`, `search_max_top_k`) and minimum similarity filtering (`search_min_similarity`).
- Frontend pagination size for query results (`search_results_page_size`).
- Allowed upload formats (`supported_image_formats`, defaulting to JPG/JPEG/JFIF/PNG/GIF/BMP/TIFF/WebP).

You can override any value with environment variables prefixed by `VISUAL_SEARCH_`, or by placing the same entries inside a `.env` file in the repo root. Examples:

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

## API & UI Endpoints
- Frontend SPA: http://localhost:3000
- REST API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Key routes:
  - `POST /search` – run similarity search (returns all matches ≥ configured confidence)
  - `POST /add-product` – upload a new catalog image (used by the catalog browser)
  - `GET /catalog/items` – paginated catalog listing (`page`, `page_size≤200`)
  - `DELETE /catalog/{product_id}` – remove a catalog entry (index rebuilds automatically)
  - `GET /catalog` – legacy full catalog dump (unchanged)
  - `GET /stats` – frontend boot metadata (page sizes, supported formats, etc.)

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
