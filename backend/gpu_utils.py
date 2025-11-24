from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import torch


@dataclass(frozen=True)
class DeviceStatus:
    """Normalized representation of the accelerator currently available."""

    device: torch.device
    description: str
    backend: str
    has_accelerator: bool


def _detect_device() -> DeviceStatus:
    """Resolve the preferred torch.device and memoize the result."""
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return DeviceStatus(
            device=torch.device("cuda"),
            description=f"CUDA GPU detected: {name}",
            backend="cuda",
            has_accelerator=True,
        )
    if torch.backends.mps.is_available():
        return DeviceStatus(
            device=torch.device("mps"),
            description="Apple Metal Performance Shaders (MPS) GPU detected",
            backend="mps",
            has_accelerator=True,
        )
    return DeviceStatus(
        device=torch.device("cpu"),
        description="No compatible GPU detected, using CPU",
        backend="cpu",
        has_accelerator=False,
    )


@lru_cache(maxsize=1)
def _device_status() -> DeviceStatus:
    return _detect_device()


def detect_gpu():
    """
    Detect if GPU acceleration is available via PyTorch.
    Returns: (has_gpu: bool, description: str)
    """
    status = _device_status()
    return status.has_accelerator, status.description


def bannerize_gpu_status():
    """Return a banner string describing the current accelerator."""
    status = _device_status()
    lines = [
        "",
        "=" * 60,
        f"GPU Configuration: {status.description}",
        "=" * 60,
        "",
    ]
    return status.has_accelerator, "\n".join(lines)


def get_device_name():
    status = _device_status()
    return status.description if status.has_accelerator else "CPU"


def resolve_torch_device(force_cpu: bool = False):
    """
    Return the best torch.device available alongside a human-readable description.
    """
    if force_cpu:
        return torch.device("cpu"), "Forced CPU execution"
    status = _device_status()
    return status.device, status.description
