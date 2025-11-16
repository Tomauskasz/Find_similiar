from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import cv2
from typing import List
import os
from pathlib import Path

from .feature_extractor import FeatureExtractor
from .similarity_search import SimilaritySearchEngine
from .models import Product, SearchResult
from .gpu_utils import bannerize_gpu_status


def generate_query_variants(image: np.ndarray) -> List[np.ndarray]:
    variants = [image]

    flipped = np.fliplr(image)
    variants.append(flipped)

    crop_ratio = 0.9
    h, w, _ = image.shape
    ch = max(1, int(h * crop_ratio))
    cw = max(1, int(w * crop_ratio))
    top = max(0, (h - ch) // 2)
    left = max(0, (w - cw) // 2)
    cropped = image[top:top + ch, left:left + cw]
    cropped = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    variants.append(cropped)

    return variants

CATALOG_DIR = Path("data/catalog")
INDEX_BASE_PATH = Path("data/catalog_index")

app = FastAPI(title="Visual Search API", version="1.0.0")
app.mount("/data", StaticFiles(directory="data"), name="data")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure GPU
_, gpu_banner = bannerize_gpu_status()
print(gpu_banner)

# Initialize services
feature_extractor = FeatureExtractor()
search_engine = SimilaritySearchEngine()

# Load catalog on startup
@app.on_event("startup")
async def startup_event():
    """Load existing catalog and build index"""
    def rebuild_index():
        global search_engine
        print("Building catalog index from images...")
        search_engine = SimilaritySearchEngine(feature_dim=feature_extractor.feature_dim)
        search_engine.build_index_from_directory(str(CATALOG_DIR), feature_extractor)
        print(f"Loaded {search_engine.get_catalog_size()} products")
        if search_engine.get_catalog_size() > 0:
            search_engine.save_index(str(INDEX_BASE_PATH))
            print("Cached catalog index to disk.")

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    index_base = INDEX_BASE_PATH
    index_files_exist = index_base.with_suffix(".index").exists() and index_base.with_suffix(".pkl").exists()

    if index_files_exist:
        try:
            print("Loading precomputed catalog index...")
            search_engine.load_index(str(index_base))
            missing = [
                product for product in search_engine.products
                if not Path(product.image_path).exists()
            ]
            if search_engine.index.d != feature_extractor.feature_dim:
                print("Cached index dimension mismatch with current feature extractor. Rebuilding index...")
                rebuild_index()
                return
            if missing:
                print(f"Detected {len(missing)} missing image files. Rebuilding index...")
                rebuild_index()
            else:
                print(f"Loaded {search_engine.get_catalog_size()} products from cache")
                return
        except Exception as exc:
            print(f"Failed to load cached index: {exc}. Rebuilding...")
            rebuild_index()
            return
    else:
        rebuild_index()

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
        
        # Read image with OpenCV
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Convert BGR to RGB
        if image is None:
            raise HTTPException(status_code=400, detail="Unable to decode image. Please try another file.")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        variants = generate_query_variants(image)
        feature_list = [feature_extractor.extract_features(variant) for variant in variants]
        query_features = np.mean(feature_list, axis=0)
        norm = np.linalg.norm(query_features)
        if norm > 0:
            query_features = query_features / norm
        
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
        # Read image with OpenCV
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Convert BGR to RGB
        if image is None:
            raise HTTPException(status_code=400, detail="Unable to decode image. Please try another file.")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Generate ID if not provided
        if not product_id:
            product_id = f"prod_{len(search_engine.products)}"
        
        # Save image
        os.makedirs("data/catalog", exist_ok=True)
        image_path = Path("data/catalog") / f"{product_id}.jpg"
        # Convert RGB back to BGR for saving
        cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        
        # Extract features and add to index
        features = feature_extractor.extract_features(image)
        
        product = Product(
            id=product_id,
            name=name or product_id,
            image_path=image_path.as_posix(),
            category=category,
            price=price
        )
        
        search_engine.add_product(product, features)
        search_engine.save_index(str(INDEX_BASE_PATH))
        
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
