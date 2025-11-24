import logging
import time
from contextlib import nullcontext
from typing import Sequence

import numpy as np
import open_clip
import torch
from PIL import Image

from .gpu_utils import resolve_torch_device

logger = logging.getLogger(__name__)


class FeatureExtractor:
    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai", *, force_cpu: bool = False):
        """
        Initialize CLIP-based feature extractor.
        """
        init_start = time.perf_counter()
        self.model_name = model_name
        self.pretrained = pretrained

        self.device, device_name = resolve_torch_device(force_cpu=force_cpu)
        self.device_description = device_name

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
        )
        self.model.to(self.device)
        self.model.eval()

        self.feature_dim = self.model.visual.output_dim
        init_duration = time.perf_counter() - init_start

        logger.info("Loaded CLIP %s (%s) for feature extraction on %s", model_name, pretrained, device_name)
        print(
            "[Startup] Feature extractor initialized in "
            f"{init_duration:.3f}s on device {self.device_description}"
        )

    def _prepare_tensor(self, img: np.ndarray) -> torch.Tensor:
        pil_img = Image.fromarray(img)
        tensor = self.preprocess(pil_img).unsqueeze(0).to(self.device)
        return tensor

    def _encode_batch(self, batch: torch.Tensor) -> np.ndarray:
        autocast_ctx = (
            torch.autocast(device_type="cuda", enabled=True)
            if self.device.type == "cuda"
            else nullcontext()
        )
        with torch.no_grad(), autocast_ctx:
            embeddings = self.model.encode_image(batch)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        return embeddings.cpu().numpy()

    def extract_features(self, img: np.ndarray) -> np.ndarray:
        return self.extract_features_batch([img])[0]

    def extract_features_batch(self, images: Sequence[np.ndarray]) -> np.ndarray:
        if not images:
            raise ValueError("At least one image is required for feature extraction.")
        tensors = [self._prepare_tensor(img) for img in images]
        batch = torch.cat(tensors, dim=0)
        return self._encode_batch(batch)
