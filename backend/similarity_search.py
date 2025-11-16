import faiss
import numpy as np
from typing import List
import os
import cv2
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .models import Product, SearchResult

class SimilaritySearchEngine:
    def __init__(self, feature_dim: int = 512):
        """
        Initialize FAISS index for similarity search
        """
        self.feature_dim = feature_dim
        
        # Use cosine similarity via inner product
        self.index = faiss.IndexFlatIP(feature_dim)
        
        # Store product metadata
        self.products: List[Product] = []
        self.feature_vectors = []
        
        print(f"Initialized FAISS index with dimension {feature_dim}")
    
    def add_product(self, product: Product, features: np.ndarray):
        """
        Add a product to the search index
        """
        normalized = self._normalize_vector(features)
        features_2d = normalized.reshape(1, -1).astype("float32")
        self.index.add(features_2d)
        
        # Store metadata
        self.products.append(product)
        self.feature_vectors.append(normalized)
    
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
        
        scores, indices = self.index.search(query_features, min(top_k, self.index.ntotal))
        similarities = (np.clip(scores[0], -1.0, 1.0) + 1.0) / 2.0
        
        # Build results
        results = []
        for idx, similarity in zip(indices[0], similarities):
            if idx < len(self.products):
                product = self.products[idx]
                results.append(
                    SearchResult(
                        product=product,
                        similarity_score=float(similarity)
                    )
                )
        
        return results
    
    def build_index_from_directory(
        self,
        directory: str,
        feature_extractor,
        batch_size: int = 32,
        max_workers: int = 4
    ):
        """
        Build index from images in a directory using batched feature extraction.
        """
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist")
            return
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        filepaths = [
            os.path.join(directory, filename)
            for filename in os.listdir(directory)
            if os.path.splitext(filename)[1].lower() in image_extensions
        ]
        
        if not filepaths:
            print(f"No images found in {directory}")
            return
        
        def load_image(path: str):
            img = cv2.imread(path)
            if img is None:
                raise ValueError("Failed to read image")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            product_id = os.path.splitext(os.path.basename(path))[0]
            product = Product(
                id=product_id,
                name=product_id.replace('_', ' ').title(),
                image_path=Path(path).as_posix()
            )
            return product, img
        
        batch_products: List[Product] = []
        batch_images: List[np.ndarray] = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(load_image, fp): fp for fp in filepaths}
            for future in as_completed(future_to_path):
                filepath = future_to_path[future]
                try:
                    product, img = future.result()
                    batch_products.append(product)
                    batch_images.append(img)
                except Exception as exc:
                    print(f"Error processing {filepath}: {exc}")
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
        # Save FAISS index
        faiss.write_index(self.index, f"{path}.index")
        
        # Save metadata
        with open(f"{path}.pkl", 'wb') as f:
            pickle.dump({
                'products': self.products,
                'feature_vectors': self.feature_vectors
            }, f)
    
    def load_index(self, path: str):
        """
        Load FAISS index and metadata from disk
        """
        # Load FAISS index
        self.index = faiss.read_index(f"{path}.index")
        
        # Load metadata
        with open(f"{path}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.products = data['products']
            self.feature_vectors = data['feature_vectors']
            if self.feature_vectors:
                self.feature_dim = len(self.feature_vectors[0])

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector.astype("float32")
        return (vector / norm).astype("float32")
