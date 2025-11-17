#!/usr/bin/env python
"""Install the appropriate PyTorch + Torchvision + OpenCLIP build."""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from dataclasses import dataclass

from .utils.cli import build_parser, non_negative_float, positive_int
from .utils.retry import run_with_retry

CUDA_INDEX = "https://download.pytorch.org/whl/cu118"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"
TORCH_VERSION = "2.1.2"
TORCHVISION_VERSION = "0.16.2"
OPENCLIP_VERSION = "2.24.0"


def run_pip(args: list[str], *, attempts: int, delay: float) -> None:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + args

    def invoke() -> None:
        subprocess.check_call(cmd)

    run_with_retry(invoke, attempts=attempts, delay=delay, exceptions=(subprocess.CalledProcessError,))


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


@dataclass
class InstallerConfig:
    desired_cuda: bool
    current_version: str | None
    has_cuda: bool


def needs_install(config: InstallerConfig) -> bool:
    if config.current_version is None:
        return True
    if config.desired_cuda and not config.has_cuda:
        return True
    if not config.desired_cuda and config.current_version and "cpu" not in config.current_version:
        return True
    return False


def install_torch(*, use_cuda: bool, attempts: int, delay: float) -> None:
    index = CUDA_INDEX if use_cuda else CPU_INDEX
    flavor = "CUDA 11.8" if use_cuda else "CPU"
    print(f"Installing PyTorch ({flavor}) build...")
    run_pip(
        [
            f"--index-url={index}",
            f"torch=={TORCH_VERSION}",
            f"torchvision=={TORCHVISION_VERSION}",
        ],
        attempts=attempts,
        delay=delay,
    )


def install_openclip(*, attempts: int, delay: float) -> None:
    print("Installing open-clip-torch...")
    run_pip([f"open-clip-torch=={OPENCLIP_VERSION}", "--no-deps"], attempts=attempts, delay=delay)


def main() -> int:
    parser = build_parser("Install the appropriate PyTorch build.")
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        help="Force CPU build even if CUDA hardware is detected.",
    )
    parser.add_argument(
        "--pip-retries",
        type=positive_int,
        default=2,
        help="Number of attempts for each pip installation command.",
    )
    parser.add_argument(
        "--pip-retry-delay",
        type=non_negative_float,
        default=2.0,
        help="Seconds to wait between pip retries (set to 0 to disable waiting).",
    )
    args = parser.parse_args()

    desired_cuda = False if args.force_cpu else has_system_cuda()
    version, has_cuda = current_variant()
    config = InstallerConfig(desired_cuda=desired_cuda, current_version=version, has_cuda=has_cuda)
    pip_kwargs = {"attempts": args.pip_retries, "delay": args.pip_retry_delay}

    if not needs_install(config):
        print(f"Existing PyTorch install ({version}) satisfies requirements.")
        install_openclip(**pip_kwargs)
        return 0

    try:
        install_torch(use_cuda=config.desired_cuda, **pip_kwargs)
    except subprocess.CalledProcessError as exc:
        if config.desired_cuda:
            print("CUDA installation failed, falling back to CPU build.")
            install_torch(use_cuda=False, **pip_kwargs)
        else:
            raise SystemExit(exc.returncode or 1)

    install_openclip(**pip_kwargs)

    _, has_cuda_after = current_variant()
    if config.desired_cuda and not has_cuda_after:
        print("Warning: PyTorch could not access CUDA; running in CPU mode.")
    else:
        print("PyTorch installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
