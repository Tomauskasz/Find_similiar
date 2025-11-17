from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import cv2
from typing import List
from pathlib import Path
import math

from .feature_extractor import FeatureExtractor
from .similarity_search import SimilaritySearchEngine
from .models import Product, SearchResult, CatalogPage
from .gpu_utils import bannerize_gpu_status
from .config import app_config


def generate_query_variants(image: np.ndarray) -> List[np.ndarray]:
    variants = [image]

    if app_config.query_use_horizontal_flip:
        variants.append(np.fliplr(image))

    if app_config.query_use_center_crop:
        crop_ratio = app_config.query_crop_ratio
        h, w, _ = image.shape
        ch = max(1, int(h * crop_ratio))
        cw = max(1, int(w * crop_ratio))
        top = max(0, (h - ch) // 2)
        left = max(0, (w - cw) // 2)
        cropped = image[top:top + ch, left:left + cw]
        cropped = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        variants.append(cropped)

    return variants

CATALOG_DIR = app_config.catalog_dir
INDEX_BASE_PATH = app_config.index_base_path
SUPPORTED_FORMATS_MESSAGE = (
    "Unsupported image format. Supported formats: "
    + app_config.format_supported_extensions()
    + "."
)
UPLOAD_DECODE_ERROR = "Unable to decode image. Please try another file."

app = FastAPI(title="Visual Search API", version="1.0.0")
static_files_app = StaticFiles(directory="data")
app.mount("/data", static_files_app, name="data")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Matches"],
)


def _add_cors_headers(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/asset/{requested_path:path}")
async def get_asset(requested_path: str):
    """Serve catalog assets with permissive CORS headers."""
    data_root = Path("data").resolve()
    sanitized = requested_path.lstrip("/").replace("..", "")
    candidate = (data_root / sanitized).resolve()
    if data_root not in candidate.parents and candidate != data_root:
        raise HTTPException(status_code=404, detail="Asset not found.")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found.")
    response = FileResponse(candidate)
    return _add_cors_headers(response)


def _validate_upload_file(upload: UploadFile) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix and suffix not in app_config.supported_image_formats:
        raise HTTPException(status_code=415, detail=SUPPORTED_FORMATS_MESSAGE)
    content_type = (upload.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Supported formats: {app_config.format_supported_extensions()}.",
        )


async def _decode_upload_image(
    upload: UploadFile,
    *,
    failure_detail: str = SUPPORTED_FORMATS_MESSAGE,
    failure_status: int = 415,
) -> np.ndarray:
    contents = await upload.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=failure_status, detail=failure_detail)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _build_query_features(image: np.ndarray) -> np.ndarray:
    variants = generate_query_variants(image)
    feature_list = [feature_extractor.extract_features(variant) for variant in variants]
    query_features = np.mean(feature_list, axis=0)
    norm = np.linalg.norm(query_features)
    if norm > 0:
        query_features = query_features / norm
    return query_features


def _parse_positive_int(value, *, param_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Parameter '{param_name}' must be an integer.")
    if parsed < 1:
        raise HTTPException(status_code=400, detail=f"Parameter '{param_name}' must be >= 1.")
    return parsed


def _parse_similarity_threshold(value) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Parameter 'min_similarity' must be a float between 0 and 1.")
    if not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="Parameter 'min_similarity' must be between 0 and 1.")
    return threshold


def _ensure_catalog_dir() -> Path:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    return CATALOG_DIR


def _save_catalog_image(image: np.ndarray, product_id: str) -> Path:
    catalog_dir = _ensure_catalog_dir()
    image_path = catalog_dir / f"{product_id}.jpg"
    cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return image_path


def _resolve_product_id(provided_id: str | None) -> str:
    if provided_id:
        return provided_id
    return f"prod_{len(search_engine.products)}"

# Configure GPU
_, gpu_banner = bannerize_gpu_status()
print(gpu_banner)

# Initialize services
feature_extractor = FeatureExtractor(
    model_name=app_config.feature_model_name,
    pretrained=app_config.feature_model_pretrained,
)
search_engine = SimilaritySearchEngine()


def _cache_index_to_disk():
    if app_config.cache_index_on_startup and search_engine.get_catalog_size() > 0:
        search_engine.save_index(str(INDEX_BASE_PATH))
        print("Cached catalog index to disk.")


def rebuild_index_from_disk():
    """Rebuild the FAISS index from catalog images on disk."""
    global search_engine
    print("Building catalog index from images...")
    search_engine = SimilaritySearchEngine(feature_dim=feature_extractor.feature_dim)
    search_engine.build_index_from_directory(
        str(CATALOG_DIR),
        feature_extractor,
        batch_size=app_config.index_build_batch_size,
        max_workers=app_config.index_build_workers,
    )
    print(f"Loaded {search_engine.get_catalog_size()} products")
    _cache_index_to_disk()


def load_cached_index_if_valid() -> bool:
    """Attempt to load cached FAISS index. Returns True if loaded successfully."""
    index_base = INDEX_BASE_PATH
    index_files_exist = index_base.with_suffix(".index").exists() and index_base.with_suffix(".pkl").exists()
    if not index_files_exist:
        return False
    try:
        print("Loading precomputed catalog index...")
        search_engine.load_index(str(index_base))
        missing = [
            product for product in search_engine.products
            if not Path(product.image_path).exists()
        ]
        if search_engine.index.d != feature_extractor.feature_dim:
            print("Cached index dimension mismatch with current feature extractor.")
            return False
        if missing:
            print(f"Detected {len(missing)} missing image files. Cached index invalid.")
            return False
        print(f"Loaded {search_engine.get_catalog_size()} products from cache")
        return True
    except Exception as exc:
        print(f"Failed to load cached index: {exc}")
        return False

# Load catalog on startup
@app.on_event("startup")
async def startup_event():
    """Load existing catalog and build index"""
    _ensure_catalog_dir()
    if not load_cached_index_if_valid():
        rebuild_index_from_disk()

@app.get("/")
async def root():
    return {"message": "Visual Search API", "status": "running"}

@app.post("/search", response_model=List[SearchResult])
async def search_similar(
    file: UploadFile = File(...),
    top_k: int = Form(app_config.search_default_top_k),
    min_similarity: float = Form(app_config.search_min_similarity),
):
    """
    Upload an image and get visually similar products
    """
    try:
        _validate_upload_file(file)
        image = await _decode_upload_image(file)
        query_features = _build_query_features(image)

        requested_top_k = _parse_positive_int(top_k, param_name="top_k")
        similarity_threshold = _parse_similarity_threshold(min_similarity)

        limit = max(1, min(requested_top_k, app_config.search_max_top_k))
        results = search_engine.search(query_features, top_k=limit)
        if similarity_threshold > 0:
            results = [
                result
                for result in results
                if result.similarity_score >= similarity_threshold
            ]

        total_matches = search_engine.count_matches(query_features, similarity_threshold)
        payload = [result.model_dump() for result in results]
        headers = {"X-Total-Matches": str(total_matches)}
        return JSONResponse(content=payload, headers=headers)
    
    except HTTPException:
        raise
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
        _validate_upload_file(file)
        image = await _decode_upload_image(file, failure_detail=UPLOAD_DECODE_ERROR, failure_status=400)
        
        product_id = _resolve_product_id(product_id)
        image_path = _save_catalog_image(image, product_id)
        
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
        _cache_index_to_disk()
        
        return {"message": "Product added successfully", "product_id": product_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/catalog/{product_id}")
async def delete_catalog_item(product_id: str):
    """
    Delete a product from the catalog and rebuild the index.
    """
    try:
        product = search_engine.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")

        image_path = Path(product.image_path)
        if not image_path.is_absolute():
            image_path = Path.cwd() / image_path
        if image_path.exists():
            image_path.unlink()
        removed = search_engine.remove_product(product_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Product not found.")
        _cache_index_to_disk()
        return {"message": "Product deleted successfully", "product_id": product_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog", response_model=List[Product])
async def get_catalog():
    """
    Get all products in the catalog
    """
    return search_engine.get_all_products()


@app.get("/catalog/items", response_model=CatalogPage)
async def get_catalog_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(app_config.catalog_default_page_size, ge=1),
):
    """
    Paginated catalog browser
    """
    size = min(page_size, app_config.catalog_max_page_size)
    total = search_engine.get_catalog_size()
    if total == 0:
        return CatalogPage(page=1, page_size=size, total_items=0, total_pages=0, items=[])

    total_pages = max(1, math.ceil(total / size))
    current_page = min(page, total_pages)
    start = (current_page - 1) * size
    end = start + size
    items = search_engine.products[start:end]
    return CatalogPage(
        page=current_page,
        page_size=size,
        total_items=total,
        total_pages=total_pages,
        items=items,
    )

@app.get("/stats")
async def get_stats():
    """
    Get statistics about the catalog
    """
    return {
        "total_products": search_engine.get_catalog_size(),
        "model": feature_extractor.model_name,
        "feature_dim": feature_extractor.feature_dim,
        "search_max_top_k": app_config.search_max_top_k,
        "search_min_similarity": app_config.search_min_similarity,
        "results_page_size": app_config.search_results_page_size,
        "supported_formats": list(app_config.supported_image_formats),
        "catalog_default_page_size": app_config.catalog_default_page_size,
        "catalog_max_page_size": app_config.catalog_max_page_size,
    }
