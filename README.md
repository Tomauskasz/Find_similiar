# Visual Search

Find visually similar catalog items by uploading an image. The backend extracts CLIP ViT-B/32 embeddings with PyTorch/OpenCLIP, normalizes them, and performs cosine search with FAISS. The React frontend provides drag-and-drop upload, backend readiness checks, and similarity visualizations.

## Architecture
- **Backend** (`backend/`): FastAPI, PyTorch, OpenCLIP, OpenCV, FAISS. `feature_extractor.py` wraps CLIP, `similarity_search.py` manages the FAISS index on disk (`data/catalog_index.*`), and `main.py` exposes the API plus static catalog assets under `/data`.
- **Frontend** (`frontend/`): React 18 single-page app with components such as `ImageUpload` and `SearchResults` in `src/components/`.
- **Scripts** (`scripts/`):
  - `run.bat` / `run.sh` bootstrap uv, create a Python 3.11 virtualenv, install dependencies, call `scripts/install_pytorch.py`, ensure `data/catalog/`, and launch backend/frontend dev servers.
  - `scripts/install_pytorch.py` inspects `nvidia-smi` and installs the most compatible PyTorch + Torchvision wheel (tries CUDA 12.4/12.2/12.1/11.8 builds, falling back across torch versions and to CPU when necessary) plus OpenCLIP. Flags: `--force-cpu`, `--pip-retries`, `--pip-retry-delay`.
  - `scripts/download_pass_catalog.py` downloads random samples from the PASS dataset (parallelized) into `data/catalog/`, now with shared retry logic and a `--dry-run` preview mode.

## Project Structure
| Path | What lives here | Plain-English summary |
| --- | --- | --- |
| `backend/` | FastAPI app, CLIP feature extractor, similarity engine, configuration, GPU helpers. | Handles every server action: receiving uploads, running AI models, managing the catalog, and exposing the REST API. |
| `backend/services/catalog_service.py` | Catalog business logic. | Decides when to rebuild the index, how to add/delete products, and how to page through items. |
| `backend/utils/` | Upload helpers, shared validation. | Cleans and verifies uploaded files so the backend always receives safe inputs. |
| `backend/tests/` | Pytest suites. | Quick checks that the upload validators, search engine, and catalog logic still behave after changes. |
| `frontend/` | React app. | Everything you see in the browser: upload box, confidence slider, search grid, and catalog browser. |
| `frontend/src/components/` | React UI pieces (ImageUpload, CatalogBrowser, SearchResults, etc.). | Reusable building blocks that create the full interface. |
| `frontend/src/hooks/` | Custom React hooks. | Encapsulate state machines such as polling backend health, managing confidence sliders, or paging catalog data. |
| `frontend/src/services/` | Axios client + API helpers. | Knows how to call the backend endpoints. |
| `frontend/src/utils/` | Browser-side helpers (image normalization, modal helpers, lightweight tests). | Keeps tiny utilities out of the components so they stay readable. |
| `scripts/` | Automation helpers. | `run.*` boot everything, `install_pytorch.py` installs GPU/CPU PyTorch correctly, `download_pass_catalog.py` grabs sample images. |
| `data/catalog/` | Image library (ignored by git). | Drag and drop pictures here (or use the UI) and the backend will index them on startup. |
| `data/catalog_index.*` | FAISS cache files (ignored by git). | Cache of the last index build so restarts are faster; deleted automatically when stale. |
| `.env.example` | Configuration template. | Copy to `.env` to override paths, page sizes, formats, etc. using friendly comments. |
| `CLEANUP_PLAN.md` / `REGRESSION.md` / `perf_smoke_results.md` | Process docs. | Track what changed, how we test, and performance snapshots. |

## Prerequisites
- Python 3.8-3.11 (3.11 recommended). On Windows install Python 3.11 with the `py` launcher and run the scripts from a shell *without* an active virtualenv.
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

## Getting Started
1. **Install the prerequisites once**: Python 3.11, the [uv](https://docs.astral.sh/uv/) CLI, and Node.js. All of them have point-and-click installers.
2. **Double-click `run.bat` (Windows) or run `./run.sh` (macOS/Linux)**. Let it finish; the first run can take a few minutes while AI models download.
3. **Wait for the "Backend" and "Frontend" terminals to report success.** Once the frontend compiles, the script automatically opens http://localhost:3000 for you.
4. **Populate the catalog.** The first launch shows an empty gallery. Either:
   - Close both terminals to stop the system and then run `python scripts/download_pass_catalog.py --count [number of random images to download]` to fetch random PASS photos into `data/catalog/`. After adding images, rerun `run.bat` / `run.sh` so the backend can index them. 
   - Skip the script and plan to use the "Add to catalog" button for your own catalog of images.
5. **Explore the UI.** Upload an image or browse the catalog and click "Find matches." Keep the terminals open while you test; close them when you are done. Future runs reuse the same virtual environment automatically and cache the indexes so system restarts are fast.
## Features

- Visual similarity search with drag-and-drop upload
- Catalog browser with pageable grid (up to 200 images per page), modal previews, uploads, and deletes
- CLIP ViT-B/32 embeddings (OpenCLIP) + FAISS cosine similarity with configurable minimum confidence
- Query-time augmentations (flip + crop) for robust matches
- GPU acceleration (CUDA/DirectML/MPS) with automatic fallback to CPU
- Modern React frontend with live status feedback
- REST API with interactive docs (`/docs`)

## How the AI Works
1. **You choose a photo.** The browser either uses the file you dragged in or, if you are in the catalog browser, quietly downloads the picture you clicked. That single snapshot becomes the “question” you are asking the system.
2. **The backend “describes” the photo with numbers.** A CLIP model (short for Contrastive Language–Image Pretraining, think of it as a camera with a fantastic memory) studies the picture for unique features like the colors, textures, and shapes in the image, then writes those observations as 512 numbers called an *embedding*. Two images that look alike end up with number lists that look alike.
3. **All catalog images already have embeddings.** During startup the server walks through everything inside `data/catalog/`, generates the same type of 512-number description once per image, and saves those in a special file so the work does not have to be repeated every time you search.
4. **We compare the query embedding with the catalog embeddings.** FAISS (short for Facebook AI Similarity Search), a search tool built for numbers, lines up the new list of 512 numbers against the stored lists and checks how close they are. If the numbers point in the same direction (high cosine similarity), we treat the underlying images as strong visual matches.
5. **We filter by confidence.** The slider you see in the app sets the minimum similarity score you are comfortable with. Anything below that percentage stays hidden, which means you control whether you see only near-identical matches or a wider mix of “maybe” results.
6. **Results go back to the browser.** The frontend shows the original query image for reference, the ordered list of best matches, and a count of how many catalog entries met your threshold. Clicking any result can immediately launch the next search using that product as the new query, so you can keep exploring without starting over.

### Visual Flow
```
 [You pick an image] ──▶ [Browser sends file] ──▶ [Backend validates] ──▶ [CLIP embedding]
        │                                                                             │
        │                                     ┌──────────── Catalog preprocessing ────┘
        ▼                                     │
 [React UI] ◀─ [Confidence filter] ◀─ [FAISS index] ◀───── precomputed embeddings
   displays       hides weak matches        stores vectors
```

## Technical Details (Under the Hood)
- **Model & embeddings**: We use OpenAI’s CLIP ViT-B/32 weights loaded through OpenCLIP. Images are resized, optionally flipped/cropped for augmentation, and normalized before the model produces a 512‑dimension embedding.
- **Similarity math**: Cosine similarity converts to a 0–1 range for the UI (`(cos + 1) / 2`). The backend counts matches directly in cosine space for accuracy.
- **Indexing**: `SimilaritySearchEngine` stores product metadata, FAISS IDs, and a feature matrix cache. Rebuilds happen automatically if the disk catalog changes or the cached index is stale. New uploads are inserted at the front of the catalog list so they appear immediately.
- **Catalog storage**: Files live under `data/catalog/`. The `/asset/...` endpoint serves them with permissive CORS headers so the React app can display them without duplication.
- **API surface**: FastAPI routers live in `backend/main.py`. We keep handlers thin and push work into `CatalogService`, `FeatureExtractor`, and utility modules for easier testing.
- **Frontend state management**: Custom hooks (`useSearchResults`, `useConfidence`, `useCatalogView`, `useBackendStats`) centralize state transitions. Components stay declarative and focus on layout.
- **Automation and installs**: `run.*` orchestrate uv, virtualenvs, PyTorch installers (CUDA-aware), frontend installs, and dev servers in one go. Everything logs its progress so non-technical users can follow along.

## Catalog Data (PASS)
To prefill the gallery with sample images, **stop the backend first** (close both terminal windows) and then run:
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

If you prefer to curate your own catalog, skip the download script entirely and use the Catalog Browser’s **Add to catalog** button instead. Those uploads are saved under `data/catalog/` and indexed immediately.

## Configuration
All important knobs live in `backend/config.py` (`AppConfig`). Override anything via a `.env` file (repo root) or `VISUAL_SEARCH_*` environment variables—use `.env.example` as a template. Every setting is validated at startup so invalid values fail fast instead of causing runtime surprises.

### Key Settings

| Setting | Env Var | Default | Notes |
| --- | --- | --- | --- |
| `catalog_dir` | `VISUAL_SEARCH_CATALOG_DIR` | `data/catalog` | Directory where catalog imagery is stored. |
| `index_base_path` | `VISUAL_SEARCH_INDEX_BASE_PATH` | `data/catalog_index` | Base path for FAISS cache files (creates `.index` + `.pkl`). |
| `index_build_batch_size` | `VISUAL_SEARCH_INDEX_BUILD_BATCH_SIZE` | `32` | Min `1`. Batch size for feature extraction when rebuilding the index. |
| `index_build_workers` | `VISUAL_SEARCH_INDEX_BUILD_WORKERS` | `4` | Min `1`. Thread pool size for catalog ingestion. |
| `cache_index_on_startup` | `VISUAL_SEARCH_CACHE_INDEX_ON_STARTUP` | `true` | If `true`, saves FAISS cache after building to speed future startups. |
| `catalog_default_page_size` | `VISUAL_SEARCH_CATALOG_DEFAULT_PAGE_SIZE` | `40` | Min `1`. Default page size for the catalog browser. |
| `catalog_max_page_size` | `VISUAL_SEARCH_CATALOG_MAX_PAGE_SIZE` | `200` | Must be = default. Hard limit for catalog pagination. |
| `feature_model_name` | `VISUAL_SEARCH_FEATURE_MODEL_NAME` | `ViT-B-32` | CLIP/OpenCLIP backbone. |
| `feature_model_pretrained` | `VISUAL_SEARCH_FEATURE_MODEL_PRETRAINED` | `openai` | Weights identifier passed to OpenCLIP. |
| `query_use_horizontal_flip` | `VISUAL_SEARCH_QUERY_USE_HORIZONTAL_FLIP` | `true` | Adds flipped variant during search. |
| `query_use_center_crop` | `VISUAL_SEARCH_QUERY_USE_CENTER_CROP` | `true` | Adds cropped variant during search. |
| `query_crop_ratio` | `VISUAL_SEARCH_QUERY_CROP_RATIO` | `0.9` | Must be `0 < ratio = 1`. Size of the retained crop. |
| `search_default_top_k` | `VISUAL_SEARCH_SEARCH_DEFAULT_TOP_K` | `200` | Min `1`. Used when clients omit `top_k`. |
| `search_max_top_k` | `VISUAL_SEARCH_SEARCH_MAX_TOP_K` | `1000` | Must be = default. Guards against unbounded searches. |
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
  - `POST /search` - run similarity search (returns all matches = configured confidence)
  - `POST /add-product` - upload a new catalog image (used by the catalog browser)
  - `GET /catalog/items` - paginated catalog listing (`page`, `page_size=200`)
  - `DELETE /catalog/{product_id}` - remove a catalog entry (index rebuilds automatically)
- `GET /catalog` - full catalog dump
- `GET /stats` - frontend boot metadata (page sizes, supported formats, etc.)

### Response Details

- `POST /search` returns a JSON array of `SearchResult` objects (`product` + `similarity_score`) and emits an `X-Total-Matches` response header indicating how many catalog entries met the requested `min_similarity`. Clients can use that header to show aggregate result counts without fetching another page.
```json
[
  {
    "product": {
      "id": "prod_42",
      "name": "Blue Denim Jacket",
      "image_path": "data/catalog/prod_42.jpg"
    },
    "similarity_score": 0.9321
  }
]
```
Response header example: `X-Total-Matches: 1182`.

- `POST /add-product` and `DELETE /catalog/{product_id}` both respond with `{ "message": "...", "product_id": "..." }` payloads so the UI can attribute toast/alert text to a specific catalog entry.
```json
{
  "message": "Product added successfully",
  "product_id": "custom_123"
}
```

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
`scripts/install_pytorch.py` inspects `nvidia-smi`, chooses the highest CUDA channel your GPU supports (12.4 ⇒ `cu124`, 12.2 ⇒ `cu122`, 12.1 ⇒ `cu121`, 11.8 ⇒ `cu118`), and then iterates through known PyTorch/Torchvision release pairs (`2.5.1/0.20.1`, `2.4.1/0.19.1`, `2.3.1/0.18.1`, `2.1.2/0.16.2`). If a wheel is missing on the channel, it automatically tries the next release before falling back to the CPU index. You can override the detection with `--force-cpu`. At runtime `backend/gpu_utils.py` logs the detected accelerator (CUDA, MPS, or CPU). No TensorFlow/DirectML code remains.

## Troubleshooting
- **Python version errors**: ensure `py -3.11` (Windows) or `python3.11` (Unix) is installed; PyTorch wheels are only available for 3.8-3.11.
- **Missing frontend assets**: delete `frontend/node_modules` and rerun `npm install`.
- **Image 404s / duplicates**: confirm referenced files exist under `data/catalog/`. Use the catalog browser delete button to remove broken entries-the backend rebuilds FAISS automatically.
- **PyTorch install failures**: rerun `python scripts/install_pytorch.py --force-cpu` inside `venv` or follow https://pytorch.org/get-started/locally/ for custom CUDA builds.

## Validation
- Backend tests: `venv\Scripts\python.exe -m pytest backend/tests`
- Frontend smoke: `npm start` (verify uploads, catalog browse, find matches)

## Performance Smoke Tests
- Catalog rebuild timing: measure how long FAISS rebuilds after running `python scripts/download_pass_catalog.py --count 1 --dry-run --insecure` and starting the backend.
- Search latency: run `npm start`, upload representative images, and note `/search` response times.

















