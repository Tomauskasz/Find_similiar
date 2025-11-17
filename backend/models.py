from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    image_path: str
    category: Optional[str] = None
    price: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    product: Product
    similarity_score: float


class CatalogPage(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[Product]


class MessageResponse(BaseModel):
    message: str = Field(..., description="Human-readable status message describing the result.")


class ProductMutationResponse(MessageResponse):
    product_id: str = Field(..., description="Identifier of the product that was created, updated, or deleted.")


class AddProductResponse(ProductMutationResponse):
    """Response returned after successfully adding a catalog product."""


class DeleteProductResponse(ProductMutationResponse):
    """Response returned after deleting a catalog product."""


class CatalogStats(BaseModel):
    total_products: int
    model: str
    feature_dim: int
    search_max_top_k: int
    search_min_similarity: float
    results_page_size: int
    supported_formats: List[str]
    catalog_default_page_size: int
    catalog_max_page_size: int
