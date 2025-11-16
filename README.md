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

## API & UI Endpoints
- Frontend SPA: http://localhost:3000
- REST API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Key routes: `POST /search`, `POST /add-product`, `GET /catalog`, `GET /stats`

## GPU Acceleration
`scripts/install_pytorch.py` prefers CUDA 11.8 wheels when `nvidia-smi` exists; otherwise it installs CPU wheels. At runtime `backend/gpu_utils.py` logs the detected accelerator (CUDA, MPS, or CPU). No TensorFlow/DirectML code remains.

## Troubleshooting
- **Python version errors**: ensure `py -3.11` (Windows) or `python3.11` (Unix) is installed; PyTorch wheels are only available for 3.8–3.11.
- **Missing frontend assets**: delete `frontend/node_modules` and rerun `npm install`.
- **Image 404s / duplicates**: confirm referenced files exist under `data/catalog/` and restart the backend so the FAISS cache refreshes.
- **PyTorch install failures**: rerun `python scripts/install_pytorch.py --force-cpu` inside `venv` or follow https://pytorch.org/get-started/locally/ for custom CUDA builds.

## Contributing
Follow the service structure above, keep functions typed, prefer async in the frontend when calling Axios, and add Pytest / React Testing Library smoke tests alongside new features. Document any `.env` changes and avoid committing large binaries or proprietary datasets.