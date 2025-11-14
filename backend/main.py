from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import io
from typing import List
import os

from .feature_extractor import FeatureExtractor
from .similarity_search import SimilaritySearchEngine
from .models import Product, SearchResult

app = FastAPI(title="Visual Search API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
feature_extractor = FeatureExtractor()
search_engine = SimilaritySearchEngine()

# Load catalog on startup
@app.on_event("startup")
async def startup_event():
    """Load existing catalog and build index"""
    catalog_dir = "data/catalog"
    if os.path.exists(catalog_dir):
        print("Loading catalog...")
        search_engine.build_index_from_directory(catalog_dir, feature_extractor)
        print(f"Loaded {search_engine.get_catalog_size()} products")

@app.get("/")
async def root():
    return {"message": "Visual Search API", "status": "running"}

@app.post("/search", response_model=List[SearchResult])
async def search_similar(
    file: UploadFile = File(...),
    top_k: int = 10
):
    """
    Upload an image and get visually similar products
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        # Extract features
        query_features = feature_extractor.extract_features(image)
        
        # Search for similar items
        results = search_engine.search(query_features, top_k=top_k)
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-product")
async def add_product(
    file: UploadFile = File(...),
    product_id: str = None,
    name: str = None,
    category: str = None,
    price: float = None
):
    """
    Add a new product to the catalog
    """
    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        # Generate ID if not provided
        if not product_id:
            product_id = f"prod_{len(search_engine.products)}"
        
        # Save image
        os.makedirs("data/catalog", exist_ok=True)
        image_path = f"data/catalog/{product_id}.jpg"
        image.save(image_path)
        
        # Extract features and add to index
        features = feature_extractor.extract_features(image)
        
        product = Product(
            id=product_id,
            name=name or product_id,
            image_path=image_path,
            category=category,
            price=price
        )
        
        search_engine.add_product(product, features)
        
        return {"message": "Product added successfully", "product_id": product_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog", response_model=List[Product])
async def get_catalog():
    """
    Get all products in the catalog
    """
    return search_engine.get_all_products()

@app.get("/stats")
async def get_stats():
    """
    Get statistics about the catalog
    """
    return {
        "total_products": search_engine.get_catalog_size(),
        "model": feature_extractor.model_name,
        "feature_dim": feature_extractor.feature_dim
    }