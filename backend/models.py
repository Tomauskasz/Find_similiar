from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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
