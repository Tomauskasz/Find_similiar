from pydantic import BaseModel
from typing import Optional, Dict, Any

class Product(BaseModel):
    id: str
    name: str
    image_path: str
    category: Optional[str] = None
    price: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = {}

class SearchResult(BaseModel):
    product: Product
    similarity_score: float