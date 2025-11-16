#!/usr/bin/env python
"""Install the appropriate PyTorch + Torchvision + OpenCLIP build."""

from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys

CUDA_INDEX = "https://download.pytorch.org/whl/cu118"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"
TORCH_VERSION = "2.1.2"
TORCHVISION_VERSION = "0.16.2"
OPENCLIP_VERSION = "2.24.0"


def run_pip(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + args
    subprocess.check_call(cmd)


def current_variant() -> tuple[str | None, bool]:
    try:
        torch = importlib.import_module("torch")
        version = getattr(torch, "__version__", "")
        has_cuda = torch.cuda.is_available()
        return version, has_cuda
    except ModuleNotFoundError:
        return None, False


def has_system_cuda() -> bool:
    return shutil.which("nvidia-smi") is not None


def install_cuda() -> None:
    print("Installing PyTorch (CUDA 11.8) build...")
    run_pip(
        [
            f"--index-url={CUDA_INDEX}",
            f"torch=={TORCH_VERSION}",
            f"torchvision=={TORCHVISION_VERSION}",
        ]
    )


def install_cpu() -> None:
    print("Installing PyTorch CPU build...")
    run_pip(
        [
            f"--index-url={CPU_INDEX}",
            f"torch=={TORCH_VERSION}",
            f"torchvision=={TORCHVISION_VERSION}",
        ]
    )


def install_openclip() -> None:
    print("Installing open-clip-torch...")
    run_pip([f"open-clip-torch=={OPENCLIP_VERSION}", "--no-deps"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the appropriate PyTorch build.")
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        help="Force CPU build even if CUDA hardware is detected.",
    )
    args = parser.parse_args()

    desired_cuda = False if args.force_cpu else has_system_cuda()
    version, has_cuda = current_variant()

    needs_install = version is None
    if version:
        if desired_cuda and not has_cuda:
            needs_install = True
        if not desired_cuda and version and "cpu" not in version:
            needs_install = True

    if not needs_install:
        print(f"Existing PyTorch install ({version}) satisfies requirements.")
        install_openclip()
        return 0

    try:
        if desired_cuda:
            install_cuda()
        else:
            install_cpu()
    except subprocess.CalledProcessError as exc:
        if desired_cuda:
            print("CUDA installation failed, falling back to CPU build.")
            install_cpu()
        else:
            raise SystemExit(exc.returncode or 1)

    install_openclip()

    _, has_cuda_after = current_variant()
    if desired_cuda and not has_cuda_after:
        print("Warning: PyTorch could not access CUDA; running in CPU mode.")
    else:
        print("PyTorch installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
