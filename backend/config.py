from pathlib import Path
from typing import Tuple

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Central configuration for the Visual Search system."""

    model_config = SettingsConfigDict(
        env_prefix="VISUAL_SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

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
    query_crop_ratio: float = Field(default=0.8, description="Percent of the image kept when center-cropping.")

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

    def format_supported_extensions(self) -> str:
        return ", ".join(ext.lstrip(".").upper() for ext in self.supported_image_formats)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator(
        "index_build_batch_size",
        "index_build_workers",
        "catalog_default_page_size",
        "catalog_max_page_size",
        "search_default_top_k",
    )
    @classmethod
    def _validate_positive_int(cls, value: int, info):
        if value < 1:
            raise ValueError(f"{info.field_name} must be >= 1.")
        return value

    @field_validator("query_crop_ratio")
    @classmethod
    def _validate_crop_ratio(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("query_crop_ratio must be between 0 (exclusive) and 1 (inclusive).")
        return value

    @field_validator("search_min_similarity")
    @classmethod
    def _validate_similarity(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("search_min_similarity must be between 0 and 1.")
        return value

    @field_validator("search_results_page_size")
    @classmethod
    def _validate_results_page_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("search_results_page_size must be >= 1.")
        return value

    @field_validator("supported_image_formats")
    @classmethod
    def _normalize_formats(cls, value: Tuple[str, ...]) -> Tuple[str, ...]:
        normalized: list[str] = []
        for ext in value:
            formatted = ext.strip().lower()
            if not formatted:
                continue
            if not formatted.startswith("."):
                formatted = f".{formatted}"
            if formatted not in normalized:
                normalized.append(formatted)
        if not normalized:
            raise ValueError("supported_image_formats must include at least one extension.")
        return tuple(normalized)

    @model_validator(mode="after")
    def _validate_relationships(self) -> "AppConfig":
        if self.catalog_max_page_size < self.catalog_default_page_size:
            raise ValueError("catalog_max_page_size must be >= catalog_default_page_size.")
        if self.search_max_top_k < self.search_default_top_k:
            raise ValueError("search_max_top_k must be >= search_default_top_k.")
        return self


app_config = AppConfig()
