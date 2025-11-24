import logging
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Union

import cv2
import faiss
import numpy as np

from .models import Product, SearchResult

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
logger = logging.getLogger(__name__)


class SimilaritySearchEngine:
    _COSINE_MIN = -1.0
    _COSINE_MAX = 1.0

    def __init__(self, feature_dim: int = 512):
        """
        Initialize FAISS index for similarity search
        """
        self.feature_dim = feature_dim
        self.backend_description = "CPU (FAISS IndexFlatIP)"
        self._init_index()
        self.products: List[Product] = []
        self.feature_vectors: Dict[str, np.ndarray] = {}
        self.product_lookup: Dict[str, Product] = {}
        self.product_id_to_faiss_id: Dict[str, int] = {}
        self.faiss_id_to_product_id: Dict[int, str] = {}
        self.next_faiss_id: int = 0
        self._feature_matrix_cache: Optional[np.ndarray] = None
        logger.info("Initialized FAISS index with dimension %s", feature_dim)

    def _init_index(self):
        # Use cosine similarity via inner product with ID mapping
        base_index = faiss.IndexFlatIP(self.feature_dim)
        cpu_index = faiss.IndexIDMap2(base_index)
        self.index = cpu_index

    def _cpu_index_for_persistence(self) -> faiss.Index:
        return self.index

    def reset(self):
        """Reset index and metadata."""
        self._init_index()
        self.products = []
        self.feature_vectors = {}
        self.product_lookup = {}
        self.product_id_to_faiss_id = {}
        self.faiss_id_to_product_id = {}
        self.next_faiss_id = 0
        self._feature_matrix_cache = None

    def _register_product(
        self,
        product: Product,
        normalized_vector: np.ndarray,
        faiss_id: int,
        *,
        position: str = "end",
    ):
        if product.id in self.product_lookup:
            self.remove_product(product.id)
        if position == "front":
            self.products.insert(0, product)
        else:
            self.products.append(product)
        self.product_lookup[product.id] = product
        self.product_id_to_faiss_id[product.id] = faiss_id
        self.faiss_id_to_product_id[faiss_id] = product.id
        self.feature_vectors[product.id] = normalized_vector
        self._feature_matrix_cache = None

    def add_product(self, product: Product, features: np.ndarray, *, position: str = "end"):
        """
        Add a product to the search index
        """
        normalized = self._normalize_vector(features)
        features_2d = normalized.reshape(1, -1).astype("float32")
        faiss_id = self.next_faiss_id
        self.next_faiss_id += 1
        ids = np.array([faiss_id], dtype="int64")
        self.index.add_with_ids(features_2d, ids)
        self._register_product(product, normalized, faiss_id, position=position)

    def search(self, query_features: np.ndarray, top_k: int = 10) -> List[SearchResult]:
        """
        Search for similar products
        """
        if self.index.ntotal == 0:
            return []

        query_features = self._normalize_vector(query_features).reshape(1, -1).astype("float32")

        scores, ids = self.index.search(query_features, min(top_k, self.index.ntotal))
        similarities = self._to_client_similarity(scores[0])

        results = []
        for faiss_id, similarity in zip(ids[0], similarities):
            if faiss_id < 0:
                continue
            product_id = self.faiss_id_to_product_id.get(int(faiss_id))
            if not product_id:
                continue
            product = self.product_lookup.get(product_id)
            if not product:
                continue
            results.append(
                SearchResult(
                    product=product,
                    similarity_score=float(similarity),
                )
            )

        return results

    def build_index_from_directory(
        self,
        directory: Union[str, Path],
        feature_extractor,
        batch_size: int = 32,
        max_workers: int = 4,
    ):
        """
        Build index from images in a directory using batched feature extraction.
        """
        root = Path(directory)
        if not root.exists():
            logger.warning("Directory %s does not exist", root)
            return

        image_paths = [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
        if not image_paths:
            logger.warning("No images found in %s", root)
            self.reset()
            return

        self.reset()

        def load_image(path: Path):
            img = cv2.imread(str(path))
            if img is None:
                raise ValueError("Failed to read image")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            product_id = path.stem
            product = Product(
                id=product_id,
                name=product_id.replace("_", " ").title(),
                image_path=path.as_posix(),
            )
            return product, img

        batch_products: List[Product] = []
        batch_images: List[np.ndarray] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(load_image, path): path for path in image_paths}
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    product, img = future.result()
                    batch_products.append(product)
                    batch_images.append(img)
                except Exception as exc:
                    logger.warning("Error processing %s: %s", path, exc)
                    continue

                if len(batch_images) >= batch_size:
                    self._process_batch(batch_products, batch_images, feature_extractor)
                    batch_products, batch_images = [], []

        if batch_images:
            self._process_batch(batch_products, batch_images, feature_extractor)

    def _process_batch(self, products: List[Product], images: List[np.ndarray], feature_extractor):
        if not products:
            return
        try:
            features_batch = feature_extractor.extract_features_batch(images)
            for product, features in zip(products, features_batch):
                self.add_product(product, features)
        except Exception as exc:
            logger.warning("Error extracting batch features: %s", exc)

    def get_all_products(self) -> List[Product]:
        """
        Get all products in the catalog
        """
        return self.products

    def get_catalog_size(self) -> int:
        """
        Get number of products in catalog
        """
        return len(self.products)

    def describe_backend(self) -> str:
        """Return a human-readable description of the FAISS execution device."""
        return self.backend_description

    def save_index(self, path: str):
        """
        Save FAISS index and metadata to disk
        """
        index_to_save = self._cpu_index_for_persistence()
        faiss.write_index(index_to_save, f"{path}.index")
        with open(f"{path}.pkl", "wb") as f:
            pickle.dump(
                {
                    "products": self.products,
                    "feature_vectors": self.feature_vectors,
                    "product_id_to_faiss_id": self.product_id_to_faiss_id,
                    "next_faiss_id": self.next_faiss_id,
                    "feature_dim": self.feature_dim,
                },
                f,
            )

    def load_index(self, path: str):
        """
        Load FAISS index and metadata from disk
        """
        cpu_index = faiss.read_index(f"{path}.index")
        self.index = cpu_index
        with open(f"{path}.pkl", "rb") as f:
            data = pickle.load(f)
            self.products = data.get("products", [])
            self.feature_vectors = data.get("feature_vectors", {})
            self.product_lookup = {product.id: product for product in self.products}
            self.product_id_to_faiss_id = data.get("product_id_to_faiss_id", {})
            self.faiss_id_to_product_id = {faiss_id: pid for pid, faiss_id in self.product_id_to_faiss_id.items()}
            self.next_faiss_id = data.get("next_faiss_id", len(self.products))
            self.feature_dim = data.get("feature_dim", self.feature_dim)
            self._feature_matrix_cache = None

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.product_lookup.get(product_id)

    def remove_product(self, product_id: str) -> Optional[Product]:
        faiss_id = self.product_id_to_faiss_id.get(product_id)
        if faiss_id is None:
            return None
        selector = faiss.IDSelectorArray(np.array([faiss_id], dtype="int64"))
        self.index.remove_ids(selector)
        removed_product = self.product_lookup.pop(product_id, None)
        self.product_id_to_faiss_id.pop(product_id, None)
        self.faiss_id_to_product_id.pop(faiss_id, None)
        self.feature_vectors.pop(product_id, None)
        self.products = [p for p in self.products if p.id != product_id]
        self._feature_matrix_cache = None
        return removed_product

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector.astype("float32")
        return (vector / norm).astype("float32")

    def count_matches(self, query_features: np.ndarray, threshold: float) -> int:
        """
        Count how many catalog items meet or exceed the provided cosine similarity threshold.
        """
        feature_matrix = self._get_feature_matrix()
        if feature_matrix is None:
            return 0

        cosine_threshold = self._from_client_threshold(threshold)
        if cosine_threshold <= self._COSINE_MIN:
            return len(self.feature_vectors)

        normalized_query = self._normalize_vector(query_features)
        similarities = feature_matrix @ normalized_query.astype("float32")
        similarities = np.clip(similarities, self._COSINE_MIN, self._COSINE_MAX)
        return int(np.count_nonzero(similarities >= cosine_threshold))

    def _get_feature_matrix(self) -> Optional[np.ndarray]:
        if not self.feature_vectors:
            return None
        if (
            self._feature_matrix_cache is None
            or self._feature_matrix_cache.shape[0] != len(self.feature_vectors)
        ):
            self._feature_matrix_cache = np.stack(list(self.feature_vectors.values()))
        return self._feature_matrix_cache

    @classmethod
    def _to_client_similarity(cls, cosine_scores: np.ndarray) -> np.ndarray:
        """Map cosine scores (-1..1) to the 0..1 scale exposed to API clients."""
        return (np.clip(cosine_scores, cls._COSINE_MIN, cls._COSINE_MAX) + 1.0) / 2.0

    @classmethod
    def _from_client_threshold(cls, threshold: float) -> float:
        """Convert the client-provided similarity threshold back to cosine space."""
        return (threshold * 2.0) - 1.0
