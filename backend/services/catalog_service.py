import logging
import math
import time
from pathlib import Path
from typing import Optional, Tuple, List, Set, Union, Dict

import cv2
import numpy as np

from ..config import AppConfig
from ..feature_extractor import FeatureExtractor
from ..models import CatalogPage, CatalogStats, Product
from ..similarity_search import SimilaritySearchEngine

logger = logging.getLogger(__name__)


class CatalogService:
    """Encapsulates catalog indexing, search, and persistence logic."""

    def __init__(self, feature_extractor: FeatureExtractor, config: AppConfig):
        self.feature_extractor = feature_extractor
        self.config = config
        self.search_engine = self._create_search_engine()

    def _create_search_engine(self) -> SimilaritySearchEngine:
        return SimilaritySearchEngine(feature_dim=self.feature_extractor.feature_dim)

    # ------------------------------------------------------------------ #
    # Lifecycle / Index Management
    # ------------------------------------------------------------------ #
    def startup(self) -> Dict[str, Union[bool, float, int]]:
        """Ensure catalog directory exists and load or rebuild the FAISS index."""
        self.config.catalog_dir.mkdir(parents=True, exist_ok=True)
        start = time.perf_counter()
        used_cache = self._load_cached_index_if_valid()
        if not used_cache:
            self._rebuild_index_from_disk()
        duration = time.perf_counter() - start
        return {
            "used_cache": used_cache,
            "duration_seconds": duration,
            "catalog_size": self.search_engine.get_catalog_size(),
        }
    def _cache_index_to_disk(self) -> None:
        if self.config.cache_index_on_startup and self.search_engine.get_catalog_size() > 0:
            self.search_engine.save_index(str(self.config.index_base_path))
            logger.info("Cached catalog index to disk.")

    def _rebuild_index_from_disk(self) -> None:
        logger.info("Building catalog index from images...")
        self.search_engine = self._create_search_engine()
        self.search_engine.build_index_from_directory(
            self.config.catalog_dir,
            self.feature_extractor,
            batch_size=self.config.index_build_batch_size,
            max_workers=self.config.index_build_workers,
        )
        logger.info("Loaded %s products", self.search_engine.get_catalog_size())
        self._cache_index_to_disk()

    def _load_cached_index_if_valid(self) -> bool:
        index_base = self.config.index_base_path
        index_files_exist = index_base.with_suffix(".index").exists() and index_base.with_suffix(".pkl").exists()
        if not index_files_exist:
            return False
        try:
            logger.info("Loading precomputed catalog index...")
            self.search_engine.load_index(str(index_base))
            missing = [
                product
                for product in self.search_engine.products
                if not Path(product.image_path).exists()
            ]
            if self.search_engine.index.d != self.feature_extractor.feature_dim:
                logger.warning("Cached index dimension mismatch with current feature extractor.")
                return False
            if missing:
                logger.warning("Detected %s missing image files. Cached index invalid.", len(missing))
                return False
            if not self._catalog_snapshot_matches_index():
                logger.info("Catalog directory contents changed since the last cached index build.")
                return False
            logger.info("Loaded %s products from cache", self.search_engine.get_catalog_size())
            return True
        except Exception as exc:
            logger.exception("Failed to load cached index: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Catalog Operations
    # ------------------------------------------------------------------ #
    def search(
        self,
        query_features: np.ndarray,
        similarity_threshold: float,
        requested_top_k: int,
    ) -> Tuple[List, int]:
        limit = max(1, requested_top_k)
        results = self.search_engine.search(query_features, top_k=limit)
        if similarity_threshold > 0:
            results = [
                result
                for result in results
                if result.similarity_score >= similarity_threshold
            ]
        total_matches = self.search_engine.count_matches(query_features, similarity_threshold)
        return results, total_matches

    def add_product(
        self,
        image: np.ndarray,
        product_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Product:
        product_id = self._resolve_product_id(product_id)
        image_path = self._save_catalog_image(image, product_id)

        features = self.feature_extractor.extract_features(image)
        product = Product(
            id=product_id,
            name=name or product_id,
            image_path=image_path.as_posix(),
        )
        self.search_engine.add_product(product, features, position="front")
        self._cache_index_to_disk()
        return product

    def delete_product(self, product_id: str) -> Product:
        product = self.search_engine.get_product(product_id)
        if not product:
            raise ValueError("Product not found.")

        image_path = self._resolve_image_path(product.image_path)
        if image_path.exists():
            image_path.unlink()

        removed = self.search_engine.remove_product(product_id)
        if not removed:
            raise ValueError("Product not found.")
        self._cache_index_to_disk()
        return product

    def get_all_products(self) -> List[Product]:
        return self.search_engine.get_all_products()

    def get_catalog_page(self, page: int, requested_size: int) -> CatalogPage:
        size = min(requested_size, self.config.catalog_max_page_size)
        total = self.search_engine.get_catalog_size()
        if total == 0:
            return CatalogPage(page=1, page_size=size, total_items=0, total_pages=0, items=[])

        total_pages = max(1, math.ceil(total / size))
        current_page = min(page, total_pages)
        start = (current_page - 1) * size
        end = start + size
        items = self.search_engine.products[start:end]
        return CatalogPage(
            page=current_page,
            page_size=size,
            total_items=total,
            total_pages=total_pages,
            items=items,
        )

    def get_stats(self) -> CatalogStats:
        return CatalogStats(
            total_products=self.search_engine.get_catalog_size(),
            model=self.feature_extractor.model_name,
            feature_dim=self.feature_extractor.feature_dim,
            search_min_similarity=self.config.search_min_similarity,
            results_page_size=self.config.search_results_page_size,
            supported_formats=list(self.config.supported_image_formats),
            catalog_default_page_size=self.config.catalog_default_page_size,
            catalog_max_page_size=self.config.catalog_max_page_size,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _resolve_image_path(self, image_path: Union[str, Path]) -> Path:
        path = Path(image_path)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    def _catalog_disk_snapshot(self) -> Set[Path]:
        if not self.config.catalog_dir.exists():
            return set()
        supported = set(self.config.supported_image_formats)
        return {
            path.resolve()
            for path in self.config.catalog_dir.iterdir()
            if path.is_file() and path.suffix.lower() in supported
        }

    def _catalog_cached_snapshot(self) -> Set[Path]:
        return {self._resolve_image_path(product.image_path) for product in self.search_engine.products}

    def _catalog_snapshot_matches_index(self) -> bool:
        disk_snapshot = self._catalog_disk_snapshot()
        cached_snapshot = self._catalog_cached_snapshot()
        if disk_snapshot != cached_snapshot:
            logger.info(
                "Catalog snapshot mismatch: %s disk files vs %s indexed entries.",
                len(disk_snapshot),
                len(cached_snapshot),
            )
            return False
        return True

    def _save_catalog_image(self, image: np.ndarray, product_id: str) -> Path:
        catalog_dir = self.config.catalog_dir
        catalog_dir.mkdir(parents=True, exist_ok=True)
        image_path = catalog_dir / f"{product_id}.jpg"
        cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return image_path

    def _resolve_product_id(self, provided_id: Optional[str]) -> str:
        if provided_id:
            return provided_id
        return f"prod_{len(self.search_engine.products)}"
