# Codebase Cleanup Plan

This document tracks the multi-pass refactor and cleanup effort for the Visual Search repository. It outlines goals, phased workstreams, and checkpoints so progress remains transparent and aligned with the Comprehensive Coding Guidelines in `AGENTS.md`.

---

## 1. Objectives

1. **Eliminate Redundancy:** Remove duplicate logic, unused assets, dead code paths, and legacy utilities.
2. **Improve Maintainability:** Clarify responsibilities, enforce single-purpose functions, and align naming with the documented standards.
3. **Optimize Hot Paths:** Revisit algorithmic complexity within feature extraction, FAISS integration, and React rendering loops.
4. **Harden Interfaces:** Ensure API contracts, component props, and internal helpers expose clearly documented, minimal surfaces.
5. **Introduce Safety Nets:** Incrementally add targeted tests around refactored areas to preserve behavior.

---

## 2. Guiding Principles

- Follow the “Comprehensive Coding Guidelines (Priority)” from `AGENTS.md`.
- Prefer small, incremental PR-sized changes even when executed sequentially here.
- Avoid speculative rewrites; each change must fix a real problem or simplify code the business relies on.
- Maintain backward compatibility for API consumers and frontend users unless explicitly approved.

---

## 3. Phase Overview

| Phase | Focus Area | Key Tasks | Status |
| --- | --- | --- | --- |
| 0 | **Planning & Inventory** | Catalog modules, identify high-risk areas, capture TODOs. | ✅ Complete |
| 1 | **Backend Core** | `backend/main.py`, `similarity_search.py`, `feature_extractor.py`, configuration & GPU helpers. Remove dead code, enforce typing, share utilities, document API responses. | 🔄 In Progress |
| 2 | **Backend Supporting Scripts** | `scripts/*.py`, run scripts, dependency management. Consolidate duplicated logic, ensure idempotence. | 🔄 In Progress |
| 3 | **Frontend State & Components** | `frontend/src/App.js`, components, hooks. Reduce prop drilling, memoize expensive computations, remove unused styles/assets. | ⬜ Pending |
| 4 | **Styles & Assets** | CSS cleanup, normalize tokens, remove unused selectors/assets, enforce consistent naming. | ⬜ Pending |
| 5 | **Documentation & Tooling** | Update README/AGENTS and add tests/tooling to match new structure. | ⬜ Pending |
| 6 | **Validation & Hardening** | Regression testing, performance smoke tests, finalize cleanup log. | ⬜ Pending |

> Each phase will receive its own checklist (see below) to keep work scoped and reviewable.

---

## 4. Detailed Phase Checklists

### Phase 1 – Backend Core
1. **Inventory Endpoints:** Confirm API route list, note unused handlers.
2. **`main.py`:**
   - Extract repeated validation (image decoding, normalization) into helpers.
   - Enforce consistent error messaging and status codes.
   - Remove global mutable state where possible; encapsulate `search_engine` interactions.
   - Document response schemas and header usage (e.g., `X-Total-Matches`). ✅ 2025-11-17: FastAPI responses now include explicit schemas/headers and README documents the `X-Total-Matches` contract.
3. **`similarity_search.py`:**
   - Deduplicate vector normalization and storage logic. (Done 2025-11-17: shared helper methods + cached feature matrix.)
   - Audit FAISS save/load logic for unused fields. (Done 2025-11-17: removed unused `product_id_to_index` metadata.)
   - Ensure `count_matches` and `search` share consistent math paths. (Done 2025-11-17: added conversion helpers to share cosine math.)
4. **`feature_extractor.py` / `gpu_utils.py`:**
   - Confirm device selection is centralized. ✅ 2025-11-17: `gpu_utils` now memoizes detection and powers all helpers via a single `DeviceStatus`.
   - Remove noisy prints or replace with structured logging. ✅ 2025-11-17: detection helpers return metadata for FastAPI logging; `FeatureExtractor` remains logger-based with stricter batch guards.
5. **Config & Settings:**
   - Validate defaults, remove unused environment variables. ✅ 2025-11-17: Added strict Pydantic validators for ratios, pagination limits, search bounds, and normalized upload formats.
   - Document every setting in code comments and README. ✅ 2025-11-17: README now includes a full configuration table with env var names + constraints.

### Phase 2 - Backend Scripts
1. Consolidate duplicated CLI argument parsing patterns. ✅ 2025-11-17: Added `scripts.utils.cli` with shared parser builder + numeric validators used by all CLI entry points.
2. Ensure downloads/installers share retry/backoff helpers. ✅ 2025-11-17: Introduced `scripts.utils.retry.run_with_retry` and wired pip installs + PASS downloads through it.
3. Remove scripts that simply wrap others without added value.
4. Add dry-run options where appropriate (e.g., catalog download). ✅ 2025-11-17: `scripts/download_pass_catalog.py --dry-run` now previews the planned URLs/files.

### Phase 3 – Frontend App & Components
1. **State Management:**
   - Audit `useState` usage; collapse related state into reducers where necessary.
   - Extract repeated API calling logic into hooks (`useBackendStats`, `useCatalog`). ✅ 2025-11-17: `useCatalog` now centralizes catalog fetching/loading/error state for `CatalogBrowser`.
2. **Components:**
   - Break down oversized components (e.g., `CatalogBrowser`, `App`). ✅ 2025-11-17: Split `CatalogBrowser` into `CatalogHero` + `CatalogCard` and moved hover logic locally to reduce prop churn.
   - Remove unused props/styles.
   - Ensure modals, sliders, and uploads share accessible patterns.
3. **Networking:**
   - Centralize Axios configuration & error handling.
   - Debounce or batch repeated calls.

### Phase 4 – Styles & Assets
1. Identify unused CSS selectors (run with tooling like `purgecss` or manual inspection).
2. Convert duplicated gradient/color definitions into CSS variables/token files.
3. Minimize global styles; scope to components when possible.

### Phase 5 – Documentation & Tooling
1. Sync README with actual dev workflow (e.g., `/asset` route, new modals).
2. Update `AGENTS.md` with any new conventions discovered during cleanup.
3. Add template tests (Pytest + RTL) covering new helper modules.

### Phase 6 – Validation
1. Manual regression checklist (uploads, catalog operations, find matches).
2. Optional performance smoke tests (index rebuild times, search latency).
3. Final review to ensure `CLEANUP_PLAN.md` tasks are all checked off.

---

## 5. Change Log Template

Each pass will add an entry below summarizing the files touched, rationale, and any required follow-up.

| Date | Phase | Summary | Notes |
| --- | --- | --- | --- |
| 2025-11-17 | Phase 2 | Added shared CLI/retry utilities, PASS catalog dry-run mode, and pip retry flags so download/install scripts share consistent backoff behavior. | Exercise both scripts when convenient to verify retry UX + dry-run output. |
| 2025-11-17 | Phase 3 | Broke `CatalogBrowser` into `CatalogHero` + `CatalogCard` subcomponents to simplify UI logic and confine hover/upload state locally. | Reconfirm catalog pagination, uploads, deletes, and modal actions. |
| 2025-11-17 | Phase 3 | Introduced `useCatalog` and refactored `CatalogBrowser` to consume it, shrinking local state and centralizing fetch/loading/error logic. | Re-test catalog pagination, uploads, deletes, and the "Find matches" action. |
| 2025-11-17 | Phase 1 | Harmonized `SimilaritySearchEngine` normalization, scoring, and count paths by sharing cosine helpers, caching feature matrices, and trimming unused metadata. | Add unit tests to ensure `count_matches` mirrors `search` thresholds. |
| 2025-11-17 | Phase 1 | Tightened `AppConfig` validation (crop ratios, search bounds, pagination limits, normalized upload formats) and documented every setting/env override in the README. | Confirm startup succeeds with custom `.env` values; add config-focused tests later. |
| 2025-11-17 | Phase 1 | Centralized GPU detection behind a memoized `DeviceStatus` helper and hardened `FeatureExtractor` batch handling so tensor prep + logging stay consistent. | Validate feature extraction on CUDA/MPS/CPU paths when possible. |
| 2025-11-17 | Phase 1 | Documented `/search` response headers plus typed add/delete/stats responses and synced README with the `X-Total-Matches` contract. | Consider adding FastAPI tests that assert header + schema behavior. |
| 2025-11-17 | Phase 1 | Added shared FastAPI upload validation/decoding helpers, normalized query feature computation, and stricter parsing utilities. Both `/search` and `/add-product` now rely on the same vetted code paths. | Manual regression pending; add unit tests for helpers. |
| 2025-11-17 | Phase 1 | Centralized catalog directory/id handling and image persistence helpers; removed duplicate logic from `/add-product` and ensured startup consistently prepares `data/catalog`. | Smoke test uploads + search when convenient. |
| 2025-11-17 | Phase 1 | Refined `SimilaritySearchEngine.build_index_from_directory` to use `pathlib`, shared extension constants, and clearer batching/logging. Removed `os` dependency and simplified file handling. | Run catalog rebuild to verify behavior when possible. |
| 2025-11-17 | Phase 1 | Unified GPU/device detection via `resolve_torch_device`, simplified `FeatureExtractor` initialization, and reused batch extraction logic to remove duplicated tensor handling. | Verify feature extraction on CPU & GPU paths if available. |
| 2025-11-17 | Phase 1 | Introduced structured logging across backend core modules (FastAPI app, similarity engine, feature extractor) to replace ad-hoc prints, improving debuggability and consistency. | Ensure logging config exists in deployment; monitor logs during next run. |
| 2025-11-17 | Phase 1 | Extracted catalog/index responsibilities into `CatalogService`, removing global state from `main.py`, consolidating cache rebuild logic, and routing all catalog operations through a single abstraction. | Validate add/delete/search endpoints and catalog pagination. |
| 2025-11-17 | Phase 1 | Moved upload/query helpers into `backend/utils/upload_utils`, trimmed unused imports, and updated routes to rely on the shared service/util stack for cleaner FastAPI handlers. | Re-test `/search` & `/add-product`; ensure `/asset` still serves images. |
| 2025-11-17 | Phase 3 | Added `useBackendStats` hook plus shared frontend image utilities, removing bespoke polling logic from `App.js` and centralizing path/blob helpers. | Verify frontend bootstraps correctly and TypeScript-style imports resolve. |
| 2025-11-17 | Phase 2 | Created `scripts/utils` helpers, refactored `download_pass_catalog.py` to reuse shared I/O utilities, and introduced a dataclass-based PyTorch installer for more predictable CLI behavior. | Re-run scripts to confirm behavior; consider adding logging configuration. |
| 2025-11-17 | Phase 3 | Introduced `useConfidence` hook and wired `SearchResults`/`CatalogBrowser` to shared image utilities, simplifying slider state management and eliminating duplicate normalization logic. | Smoke test slider + "Find matches" flow. |
| 2025-11-17 | Phase 3 | Added `useCatalogView` hook, centralized Axios usage via `apiClient`, and ensured backend polling + slider logic leverage shared hooks/utilities. | Confirm view toggling and API interactions work end-to-end. |
| 2025-11-17 | Phase 3 | Memoized search callbacks in `App.js`, renamed the shared HTTP client to avoid redeclarations, and switched `CatalogBrowser` to the shared Axios wrapper. Backend config restored after accidental removal. | Smoke-test search flow and ensure config is intact. |
| 2025-11-17 | Phase 3 | Resolved frontend build error by renaming the memoized API client instance throughout `App.js` so Babel no longer reports duplicate identifiers. | Verify frontend compiles and runs without redeclaration errors. |

---

## 6. Next Steps

1. Prioritize Phase 1 (Backend Core) and create subtasks for the first pass.
2. For each pass:
   - Update the "3. Phase Overview"
   - Update the checklist above.
   - Append an entry to the Change Log table.
   - Ensure code + documentation changes remain in sync.

This document will evolve as cleanup progresses; always update it before or alongside code changes so the plan stays authoritative.
