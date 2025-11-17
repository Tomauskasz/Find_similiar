import logging
from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List

from .feature_extractor import FeatureExtractor
from .models import (
    AddProductResponse,
    CatalogPage,
    CatalogStats,
    DeleteProductResponse,
    Product,
    SearchResult,
)
from .gpu_utils import bannerize_gpu_status
from .config import app_config
from .services.catalog_service import CatalogService
from .utils.upload_utils import (
    build_query_features,
    build_supported_formats_message,
    decode_upload_image,
    parse_positive_int,
    parse_similarity_threshold,
    validate_upload_file,
    UPLOAD_DECODE_ERROR,
)

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS_MESSAGE = build_supported_formats_message(app_config)
TOTAL_MATCHES_HEADER = "X-Total-Matches"

SEARCH_SUCCESS_RESPONSE = {
    200: {
        "description": (
            "List of catalog entries sorted by cosine similarity. "
            "The X-Total-Matches response header reports how many products meet or exceed the "
            "requested similarity threshold."
        ),
        "headers": {
            TOTAL_MATCHES_HEADER: {
                "description": "Total number of matches in the catalog at the provided similarity threshold.",
                "schema": {"type": "integer"},
            }
        },
    }
}

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


# Configure GPU
_, gpu_banner = bannerize_gpu_status()
logger.info(gpu_banner)

# Initialize services
feature_extractor = FeatureExtractor(
    model_name=app_config.feature_model_name,
    pretrained=app_config.feature_model_pretrained,
)
catalog_service = CatalogService(feature_extractor, app_config)

# Load catalog on startup
@app.on_event("startup")
async def startup_event():
    """Load existing catalog and build index"""
    catalog_service.startup()

@app.get("/")
async def root():
    return {"message": "Visual Search API", "status": "running"}

@app.post("/search", response_model=List[SearchResult], responses=SEARCH_SUCCESS_RESPONSE)
async def search_similar(
    file: UploadFile = File(...),
    top_k: int = Form(app_config.search_default_top_k),
    min_similarity: float = Form(app_config.search_min_similarity),
):
    """
    Upload an image and get visually similar products
    """
    try:
        validate_upload_file(file, app_config)
        image = await decode_upload_image(file, failure_detail=SUPPORTED_FORMATS_MESSAGE, failure_status=415)
        query_features = build_query_features(image, feature_extractor, app_config)

        requested_top_k = parse_positive_int(top_k, param_name="top_k")
        similarity_threshold = parse_similarity_threshold(min_similarity)

        results, total_matches = catalog_service.search(query_features, similarity_threshold, requested_top_k)
        payload = [result.model_dump() for result in results]
        headers = {TOTAL_MATCHES_HEADER: str(total_matches)}
        return JSONResponse(content=payload, headers=headers)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-product", response_model=AddProductResponse)
async def add_product(
    file: UploadFile = File(...),
    product_id: str | None = Form(None),
    name: str | None = Form(None),
    category: str | None = Form(None),
    price: float | None = Form(None)
):
    """
    Add a new product to the catalog
    """
    try:
        validate_upload_file(file, app_config)
        image = await decode_upload_image(file, failure_detail=UPLOAD_DECODE_ERROR, failure_status=400)
        
        product = catalog_service.add_product(
            image=image,
            product_id=product_id,
            name=name,
            category=category,
            price=price,
        )
        return AddProductResponse(message="Product added successfully", product_id=product.id)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/catalog/{product_id}", response_model=DeleteProductResponse)
async def delete_catalog_item(product_id: str):
    """
    Delete a product from the catalog and rebuild the index.
    """
    try:
        catalog_service.delete_product(product_id)
        return DeleteProductResponse(message="Product deleted successfully", product_id=product_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog", response_model=List[Product])
async def get_catalog():
    """
    Get all products in the catalog
    """
    return catalog_service.get_all_products()


@app.get("/catalog/items", response_model=CatalogPage)
async def get_catalog_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(app_config.catalog_default_page_size, ge=1),
):
    """
    Paginated catalog browser
    """
    return catalog_service.get_catalog_page(page, page_size)

@app.get("/stats", response_model=CatalogStats)
async def get_stats():
    """
    Get statistics about the catalog
    """
    return catalog_service.get_stats()
