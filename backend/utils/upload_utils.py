from typing import Optional
from pathlib import Path

import numpy as np
import cv2
from fastapi import HTTPException, UploadFile

from ..config import AppConfig
from ..feature_extractor import FeatureExtractor


UPLOAD_DECODE_ERROR = "Unable to decode image. Please try another file."


def build_supported_formats_message(config: AppConfig) -> str:
    return (
        "Unsupported image format. Supported formats: "
        + config.format_supported_extensions()
        + "."
    )


def validate_upload_file(upload: UploadFile, config: AppConfig) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix and suffix not in config.supported_image_formats:
        raise HTTPException(status_code=415, detail=build_supported_formats_message(config))
    content_type = (upload.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Supported formats: {config.format_supported_extensions()}.",
        )


async def decode_upload_image(
    upload: UploadFile,
    *,
    failure_detail: str,
    failure_status: int,
) -> np.ndarray:
    contents = await upload.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=failure_status, detail=failure_detail)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def build_query_variants(image: np.ndarray, config: AppConfig) -> list[np.ndarray]:
    variants = [image]
    if config.query_use_horizontal_flip:
        variants.append(np.fliplr(image))
    if config.query_use_center_crop:
        crop_ratio = config.query_crop_ratio
        h, w, _ = image.shape
        ch = max(1, int(h * crop_ratio))
        cw = max(1, int(w * crop_ratio))
        top = max(0, (h - ch) // 2)
        left = max(0, (w - cw) // 2)
        cropped = image[top : top + ch, left : left + cw]
        cropped = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        variants.append(cropped)
    return variants


def build_query_features(
    image: np.ndarray,
    extractor: FeatureExtractor,
    config: AppConfig,
) -> np.ndarray:
    variants = build_query_variants(image, config)
    feature_list = [extractor.extract_features(variant) for variant in variants]
    query_features = np.mean(feature_list, axis=0)
    norm = np.linalg.norm(query_features)
    if norm > 0:
        query_features = query_features / norm
    return query_features


def parse_positive_int(value, *, param_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Parameter '{param_name}' must be an integer.")
    if parsed < 1:
        raise HTTPException(status_code=400, detail=f"Parameter '{param_name}' must be >= 1.")
    return parsed


def parse_similarity_threshold(value) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Parameter 'min_similarity' must be a float between 0 and 1.")
    if not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="Parameter 'min_similarity' must be between 0 and 1.")
    return threshold
