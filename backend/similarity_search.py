import faiss
import numpy as np
from typing import List, Dict, Optional
import cv2
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .models import Product, SearchResult

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}

class SimilaritySearchEngine:
    def __init__(self, feature_dim: int = 512):
        """
        Initialize FAISS index for similarity search
        """
        self.feature_dim = feature_dim
        self._init_index()
        self.products: List[Product] = []
        self.feature_vectors: Dict[str, np.ndarray] = {}
        self.product_lookup: Dict[str, Product] = {}
        self.product_id_to_index: Dict[str, int] = {}
        self.product_id_to_faiss_id: Dict[str, int] = {}
        self.faiss_id_to_product_id: Dict[int, str] = {}
        self.next_faiss_id: int = 0
        print(f"Initialized FAISS index with dimension {feature_dim}")

    def _init_index(self):
        # Use cosine similarity via inner product with ID mapping
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.feature_dim))

    def reset(self):
        """Reset index and metadata."""
        self._init_index()
        self.products = []
        self.feature_vectors = {}
        self.product_lookup = {}
        self.product_id_to_index = {}
        self.product_id_to_faiss_id = {}
        self.faiss_id_to_product_id = {}
        self.next_faiss_id = 0

    def _register_product(self, product: Product, normalized_vector: np.ndarray, faiss_id: int):
        if product.id in self.product_lookup:
            self.remove_product(product.id)
        self.products.append(product)
        self.product_lookup[product.id] = product
        self.product_id_to_index[product.id] = len(self.products) - 1
        self.product_id_to_faiss_id[product.id] = faiss_id
        self.faiss_id_to_product_id[faiss_id] = product.id
        self.feature_vectors[product.id] = normalized_vector

    def add_product(self, product: Product, features: np.ndarray):
        """
        Add a product to the search index
        """
        normalized = self._normalize_vector(features)
        features_2d = normalized.reshape(1, -1).astype("float32")
        faiss_id = self.next_faiss_id
        self.next_faiss_id += 1
        ids = np.array([faiss_id], dtype='int64')
        self.index.add_with_ids(features_2d, ids)
        self._register_product(product, normalized, faiss_id)
    
    def search(
        self,
        query_features: np.ndarray,
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Search for similar products
        """
        if self.index.ntotal == 0:
            return []
        
        # Ensure correct shape and type
        query_features = self._normalize_vector(query_features).reshape(1, -1).astype("float32")
        
        scores, ids = self.index.search(query_features, min(top_k, self.index.ntotal))
        similarities = (np.clip(scores[0], -1.0, 1.0) + 1.0) / 2.0
        
        # Build results
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
                    similarity_score=float(similarity)
                )
            )
        
        return results
    
    def build_index_from_directory(
        self,
        directory: str | Path,
        feature_extractor,
        batch_size: int = 32,
        max_workers: int = 4,
    ):
        """
        Build index from images in a directory using batched feature extraction.
        """
        root = Path(directory)
        if not root.exists():
            print(f"Directory {root} does not exist")
            return

        image_paths = [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
        if not image_paths:
            print(f"No images found in {root}")
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
                    print(f"Error processing {path}: {exc}")
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
            print(f"Error extracting batch features: {exc}")
    
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
    
    def save_index(self, path: str):
        """
        Save FAISS index and metadata to disk
        """
        faiss.write_index(self.index, f"{path}.index")
        with open(f"{path}.pkl", 'wb') as f:
            pickle.dump(
                {
                    'products': self.products,
                    'feature_vectors': self.feature_vectors,
                    'product_id_to_faiss_id': self.product_id_to_faiss_id,
                    'next_faiss_id': self.next_faiss_id,
                    'feature_dim': self.feature_dim,
                },
                f,
            )
    
    def load_index(self, path: str):
        """
        Load FAISS index and metadata from disk
        """
        self.index = faiss.read_index(f"{path}.index")
        with open(f"{path}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.products = data.get('products', [])
            self.feature_vectors = data.get('feature_vectors', {})
            self.product_lookup = {product.id: product for product in self.products}
            self.product_id_to_index = {product.id: idx for idx, product in enumerate(self.products)}
            self.product_id_to_faiss_id = data.get('product_id_to_faiss_id', {})
            self.faiss_id_to_product_id = {faiss_id: pid for pid, faiss_id in self.product_id_to_faiss_id.items()}
            self.next_faiss_id = data.get('next_faiss_id', len(self.products))
            self.feature_dim = data.get('feature_dim', self.feature_dim)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.product_lookup.get(product_id)

    def remove_product(self, product_id: str) -> Optional[Product]:
        faiss_id = self.product_id_to_faiss_id.get(product_id)
        if faiss_id is None:
            return None
        selector = faiss.IDSelectorArray(np.array([faiss_id], dtype='int64'))
        self.index.remove_ids(selector)
        removed_product = self.product_lookup.pop(product_id, None)
        self.product_id_to_faiss_id.pop(product_id, None)
        self.faiss_id_to_product_id.pop(faiss_id, None)
        self.feature_vectors.pop(product_id, None)
        self.products = [p for p in self.products if p.id != product_id]
        self.product_id_to_index = {product.id: idx for idx, product in enumerate(self.products)}
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
        if not self.feature_vectors:
            return 0
        # Threshold provided by clients uses the 0..1 scale (after mapping cosine scores from [-1, 1]).
        # Convert back to raw cosine values for comparison with stored normalized vectors.
        cosine_threshold = (threshold * 2.0) - 1.0
        if cosine_threshold <= -1.0:
            return len(self.feature_vectors)
        normalized_query = self._normalize_vector(query_features)
        feature_matrix = np.stack(list(self.feature_vectors.values()))
        similarities = feature_matrix @ normalized_query.astype("float32")
        return int(np.sum(similarities >= cosine_threshold))
