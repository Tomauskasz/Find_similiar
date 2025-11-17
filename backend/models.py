from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

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
