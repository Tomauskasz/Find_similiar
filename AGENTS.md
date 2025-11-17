# Repository Guidelines

## Structure
- `backend/`: FastAPI app (`main.py`), CLIP feature extractor (`feature_extractor.py`), FAISS engine (`similarity_search.py`), Pydantic models (`models.py`), and GPU helpers (`gpu_utils.py`). Catalog images and FAISS cache live in `data/catalog/` and `data/catalog_index.*`.
- `backend/config.py`: Central `AppConfig` (Pydantic `BaseSettings`) controlling directories, CLIP model, query augmentations, search limits, supported formats, and catalog pagination. Override via `VISUAL_SEARCH_*` environment variables or `.env`.
- `frontend/`: React 18 app with components under `src/components/` (e.g., `ImageUpload`, `SearchResults`, `CatalogBrowser`).
- `scripts/`: Utility entry points such as `download_pass_catalog.py`, `install_pytorch.py`, plus the top-level `run.bat` / `run.sh` automation.

## Build & Dev
- Preferred loop: `run.bat` (Windows) or `run.sh` (macOS/Linux/WSL). They install uv deps, enforce Python 3.11 venvs, call `scripts/install_pytorch.py`, and start uvicorn + the React dev server.
- Manual backend command: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` (after `uv pip install -r requirements.txt` and running `python scripts/install_pytorch.py`).
- Frontend: `cd frontend && npm install && npm start`. Build for prod with `npm run build`.
- PyTorch variants: re-run `python scripts/install_pytorch.py` (`--force-cpu` optional) inside `venv` if you need to switch CUDA/CPU builds.
- Catalog API highlights: `POST /search`, `POST /add-product`, `GET /catalog/items`, `DELETE /catalog/{id}`, `GET /stats`. Keep these stable for the React catalog browser.

## Coding Style
- Python: 4-space indents, typing, descriptive snake_case. Keep FastAPI routers lean; heavy lifting belongs in helper modules/engines. Avoid mutable defaults (use `Field(default_factory=...)`).
- JavaScript/React: PascalCase components, kebab-case CSS classes, hooks with complete dependency arrays, async/await for Axios calls, API base URL from `frontend/.env` (`REACT_APP_API_URL`).

## Testing
- No automated tests exist yet—add Pytest suites under `backend/tests/` for new backend functionality (use PASS samples or fixtures). Use React Testing Library / Jest alongside frontend components (`*.test.jsx`) or under `frontend/src/__tests__/`. Disable watch mode in CI (`npm test -- --watch=false`).

## Data & Security
- Store catalog imagery in `data/catalog/` (populate via `scripts/download_pass_catalog.py`). Avoid checking in large binaries or proprietary data despite `.gitignore` excluding `venv/`.
- Backend rebuilds `data/catalog_index.*` automatically if catalog files change—do not commit cached indexes.
- Never commit secrets or `.env` files; add keys to `.env.example` when configuration changes.
- Documentation (`README.md` and `AGENTS.md`) must stay accurate. After every change to the codebase or workflows, review these files and update them if anything is outdated so they always reflect the current state.
