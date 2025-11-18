from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException

from ..config import AppConfig
from ..utils import upload_utils


class DummyUpload:
    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self):
        return self._content


class DummyExtractor:
    def __init__(self, output: np.ndarray):
        self._output = output
        self.calls: list[np.ndarray] = []

    def extract_features(self, image: np.ndarray) -> np.ndarray:
        self.calls.append(image)
        return self._output


def test_parse_positive_int_valid():
    assert upload_utils.parse_positive_int("5", param_name="top_k") == 5


@pytest.mark.parametrize("value", ["0", "abc", None])
def test_parse_positive_int_invalid(value):
    with pytest.raises(HTTPException):
        upload_utils.parse_positive_int(value, param_name="top_k")


def test_parse_similarity_threshold_valid():
    assert upload_utils.parse_similarity_threshold("0.8") == 0.8


@pytest.mark.parametrize("value", ["-0.1", "1.1", "oops"])
def test_parse_similarity_threshold_invalid(value):
    with pytest.raises(HTTPException):
        upload_utils.parse_similarity_threshold(value)


def test_build_query_features_averages_variants():
    config = AppConfig(
        query_use_horizontal_flip=True,
        query_use_center_crop=True,
        query_crop_ratio=0.5,
    )
    image = np.ones((4, 4, 3), dtype=np.uint8)
    expected_vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    extractor = DummyExtractor(expected_vector)

    features = upload_utils.build_query_features(image, extractor, config)

    assert np.allclose(features, expected_vector)
    # Horizontal flip + crop variants => 3 calls in total
    assert len(extractor.calls) == 3


def test_decode_upload_image_rejects_invalid_data():
    upload = DummyUpload("broken.jpg", "image/jpeg", b"not-an-image")

    async def call_decode():
        await upload_utils.decode_upload_image(
            upload,
            failure_detail=upload_utils.UPLOAD_DECODE_ERROR,
            failure_status=400,
        )

    with pytest.raises(HTTPException):
        asyncio.run(call_decode())
