import faiss
import numpy as np
from typing import List, Tuple
import os
from PIL import Image
import pickle

from .models import Product, SearchResult

class SimilaritySearchEngine:
    def __init__(self, feature_dim: int = 2048):
        """
        Initialize FAISS index for similarity search
        """
        self.feature_dim = feature_dim
        
        # Use L2 distance (can also use IndexFlatIP for inner product/cosine)
        self.index = faiss.IndexFlatL2(feature_dim)
        
        # Store product metadata
        self.products: List[Product] = []
        self.feature_vectors = []
        
        print(f"Initialized FAISS index with dimension {feature_dim}")
    
    def add_product(self, product: Product, features: np.ndarray):
        """
        Add a product to the search index
        """
        # Add to FAISS index
        features_2d = features.reshape(1, -1).astype('float32')
        self.index.add(features_2d)
        
        # Store metadata
        self.products.append(product)
        self.feature_vectors.append(features)
    
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
        query_features = query_features.reshape(1, -1).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_features, min(top_k, self.index.ntotal))
        
        # Convert distances to similarity scores (inverse of L2 distance)
        # Normalize to 0-1 range
        max_dist = distances[0].max() if len(distances[0]) > 0 else 1.0
        similarities = 1 - (distances[0] / (max_dist + 1e-6))
        
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
        feature_extractor
    ):
        """
        Build index from images in a directory
        """
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist")
            return
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            # Check if file is an image
            ext = os.path.splitext(filename)[1].lower()
            if ext not in image_extensions:
                continue
            
            try:
                # Load image
                img = Image.open(filepath).convert('RGB')
                
                # Extract features
                features = feature_extractor.extract_features(img)
                
                # Create product
                product_id = os.path.splitext(filename)[0]
                product = Product(
                    id=product_id,
                    name=product_id.replace('_', ' ').title(),
                    image_path=filepath
                )
                
                # Add to index
                self.add_product(product, features)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
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