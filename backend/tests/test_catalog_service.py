from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import AppConfig
from ..models import Product
from ..services.catalog_service import CatalogService


class DummyExtractor:
    def __init__(self, feature_dim: int = 4):
        self.feature_dim = feature_dim
        self.model_name = "dummy"

    def extract_features(self, image):
        return np.ones(self.feature_dim, dtype=np.float32)

    def extract_features_batch(self, images):
        return [self.extract_features(None) for _ in images]


def build_service(tmp_path: Path) -> CatalogService:
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    config = AppConfig(
        catalog_dir=catalog_dir,
        index_base_path=tmp_path / "catalog_index",
        cache_index_on_startup=False,
    )
    return CatalogService(DummyExtractor(), config)


def test_catalog_snapshot_matches_when_disk_and_cache_identical(tmp_path):
    service = build_service(tmp_path)
    image_path = service.config.catalog_dir / "prod_1.jpg"
    image_path.write_bytes(b"0")
    service.search_engine.products = [
        Product(id="prod_1", name="Prod 1", image_path=image_path.as_posix())
    ]

    assert service._catalog_snapshot_matches_index() is True


def test_catalog_snapshot_detects_new_disk_files(tmp_path):
    service = build_service(tmp_path)
    new_image = service.config.catalog_dir / "new_image.jpg"
    new_image.write_bytes(b"0")

    assert service._catalog_snapshot_matches_index() is False
