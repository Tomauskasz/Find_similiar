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
| 2 | **Backend Supporting Scripts** | `scripts/*.py`, run scripts, dependency management. Consolidate duplicated logic, ensure idempotence. | ⬜ Pending |
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
   - Document response schemas and header usage (e.g., `X-Total-Matches`).
3. **`similarity_search.py`:**
   - Deduplicate vector normalization and storage logic.
   - Audit FAISS save/load logic for unused fields.
   - Ensure `count_matches` and `search` share consistent math paths.
4. **`feature_extractor.py` / `gpu_utils.py`:**
   - Confirm device selection is centralized.
   - Remove noisy prints or replace with structured logging.
5. **Config & Settings:**
   - Validate defaults, remove unused environment variables.
   - Document every setting in code comments and README.

### Phase 2 – Backend Scripts
1. Consolidate duplicated CLI argument parsing patterns.
2. Ensure downloads/installers share retry/backoff helpers.
3. Remove scripts that simply wrap others without added value.
4. Add dry-run options where appropriate (e.g., catalog download).

### Phase 3 – Frontend App & Components
1. **State Management:**
   - Audit `useState` usage; collapse related state into reducers where necessary.
   - Extract repeated API calling logic into hooks (`useBackendStats`, `useCatalog`).
2. **Components:**
   - Break down oversized components (e.g., `CatalogBrowser`, `App`).
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
| 2025-11-17 | Phase 1 | Added shared FastAPI upload validation/decoding helpers, normalized query feature computation, and stricter parsing utilities. Both `/search` and `/add-product` now rely on the same vetted code paths. | Manual regression pending; add unit tests for helpers. |
| 2025-11-17 | Phase 1 | Centralized catalog directory/id handling and image persistence helpers; removed duplicate logic from `/add-product` and ensured startup consistently prepares `data/catalog`. | Smoke test uploads + search when convenient. |

---

## 6. Next Steps

1. Prioritize Phase 1 (Backend Core) and create subtasks for the first pass.
2. For each pass:
   - Update the checklist above.
   - Append an entry to the Change Log table.
   - Ensure code + documentation changes remain in sync.

This document will evolve as cleanup progresses; always update it before or alongside code changes so the plan stays authoritative.
