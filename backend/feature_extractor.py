import numpy as np
import torch
import open_clip
from PIL import Image
from contextlib import nullcontext

from .gpu_utils import get_device_name


class FeatureExtractor:
    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai"):
        """
        Initialize CLIP-based feature extractor.
        """
        self.model_name = model_name
        self.pretrained = pretrained

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
        )
        self.model.to(self.device)
        self.model.eval()

        self.feature_dim = self.model.visual.output_dim

        device = get_device_name()
        print(f"Loaded CLIP {model_name} ({pretrained}) for feature extraction on {device}")

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
        tensor = self._prepare_tensor(img)
        features = self._encode_batch(tensor)[0]
        return features

    def extract_features_batch(self, images: list[np.ndarray]) -> np.ndarray:
        tensors = [self._prepare_tensor(img) for img in images]
        batch = torch.cat(tensors, dim=0)
        return self._encode_batch(batch)
