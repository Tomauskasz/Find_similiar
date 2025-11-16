import torch


def detect_gpu():
    """
    Detect if GPU acceleration is available via PyTorch.
    Returns: (has_gpu: bool, description: str)
    """
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return True, f"CUDA GPU detected: {name}"
    if torch.backends.mps.is_available():
        return True, "Apple Metal Performance Shaders (MPS) GPU detected"
    return False, "No compatible GPU detected, using CPU"


def bannerize_gpu_status():
    """Return a banner string describing the current accelerator."""
    has_gpu, info = detect_gpu()
    lines = [
        "",
        "=" * 60,
        f"GPU Configuration: {info}",
        "=" * 60,
        "",
    ]
    return has_gpu, "\n".join(lines)


def get_device_name():
    has_gpu, info = detect_gpu()
    return info if has_gpu else "CPU"
