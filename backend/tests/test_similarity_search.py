from __future__ import annotations

import numpy as np
import pytest

from ..models import Product
from ..similarity_search import SimilaritySearchEngine


def create_product(idx: int) -> Product:
    return Product(id=f"prod_{idx}", name=f"Product {idx}", image_path=f"data/catalog/prod_{idx}.jpg")


def test_search_returns_sorted_results():
    engine = SimilaritySearchEngine(feature_dim=3)
    vectors = [
        np.array([1.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0], dtype=np.float32),
        np.array([0.0, 0.0, 1.0], dtype=np.float32),
    ]
    for idx, vec in enumerate(vectors):
        engine.add_product(create_product(idx), vec)

    query = np.array([0.9, 0.1, 0.0], dtype=np.float32)
    results = engine.search(query, top_k=3)
    assert len(results) == 3
    assert results[0].product.id == "prod_0"
    assert results[1].product.id == "prod_1"
    assert results[2].product.id == "prod_2"
    assert all(results[i].similarity_score >= results[i + 1].similarity_score for i in range(len(results) - 1))


@pytest.mark.parametrize(
    "threshold,expected_count",
        [
            (0.0, 3),
            (0.75, 2),
            (0.95, 2),
            (1.0, 1),
        ],
)
def test_count_matches_respects_threshold(threshold, expected_count):
    engine = SimilaritySearchEngine(feature_dim=3)
    vectors = [
        np.array([1.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.8, 0.2, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0], dtype=np.float32),
    ]
    for idx, vec in enumerate(vectors):
        engine.add_product(create_product(idx), vec)

    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert engine.count_matches(query, threshold) == expected_count
