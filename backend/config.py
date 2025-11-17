from pathlib import Path
from typing import Tuple

from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Central configuration for the Visual Search system.

    Values can be overridden via environment variables prefixed with ``VISUAL_SEARCH_``
    or by defining them inside a local ``.env`` file (see README for details).
    """

    # Catalog / index settings
    catalog_dir: Path = Field(default=Path("data/catalog"), description="Directory holding catalog imagery.")
    index_base_path: Path = Field(default=Path("data/catalog_index"), description="Base path for FAISS cache files.")
    index_build_batch_size: int = Field(default=32, description="Images per batch when building FAISS index.")
    index_build_workers: int = Field(default=4, description="Parallel workers for catalog loading.")
    cache_index_on_startup: bool = Field(default=True, description="Persist FAISS cache after building.")
    catalog_default_page_size: int = Field(default=40, description="Default number of catalog images per page.")
    catalog_max_page_size: int = Field(default=200, description="Maximum images per page in catalog browser.")

    # Feature extraction settings
    feature_model_name: str = Field(default="ViT-B-32", description="CLIP/OpenCLIP model name.")
    feature_model_pretrained: str = Field(default="openai", description="Pretrained weights identifier.")

    # Query augmentation settings
    query_use_horizontal_flip: bool = Field(default=True, description="Include a horizontal flip query variant.")
    query_use_center_crop: bool = Field(default=True, description="Include a center crop variant.")
    query_crop_ratio: float = Field(default=0.9, description="Percent of the image kept when center-cropping.")

    # Search settings
    search_default_top_k: int = Field(default=200, description="Fallback top-k when clients omit the value.")
    search_max_top_k: int = Field(default=1000, description="Upper bound to protect the service.")
    search_min_similarity: float = Field(default=0.8, description="Minimum cosine similarity to treat as a match.")
    search_results_page_size: int = Field(default=10, description="Frontend page size for the results grid.")

    # Upload validation
    supported_image_formats: Tuple[str, ...] = Field(
        default=(
            ".jpg",
            ".jpeg",
            ".jfif",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
        ),
        description="Allowed image file extensions.",
    )

    class Config:
        env_prefix = "VISUAL_SEARCH_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def format_supported_extensions(self) -> str:
        return ", ".join(ext.lstrip(".").upper() for ext in self.supported_image_formats)


app_config = AppConfig()
