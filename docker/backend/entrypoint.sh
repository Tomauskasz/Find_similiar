#!/usr/bin/env bash
set -euo pipefail

: "${VISUAL_SEARCH_CATALOG_DIR:=/app/data/catalog}"
: "${VISUAL_SEARCH_INDEX_BASE_PATH:=/app/data/catalog_index}"

mkdir -p "${VISUAL_SEARCH_CATALOG_DIR}"
mkdir -p "$(dirname "${VISUAL_SEARCH_INDEX_BASE_PATH}")"

if [[ "${SEED_CATALOG:-0}" == "1" ]]; then
  echo "Seeding catalog into ${VISUAL_SEARCH_CATALOG_DIR}..."
  python scripts/download_pass_catalog.py \
    --out "${VISUAL_SEARCH_CATALOG_DIR}" \
    --count "${SEED_CATALOG_COUNT:-200}" \
    --retry-attempts "${CATALOG_RETRY_ATTEMPTS:-3}" \
    --retry-delay "${CATALOG_RETRY_DELAY:-5}" || echo "Catalog seeding failed (continuing)."
fi

exec "$@"
