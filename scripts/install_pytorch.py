#!/usr/bin/env python
"""Install the appropriate PyTorch + Torchvision + OpenCLIP build."""

from __future__ import annotations

import importlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

if __package__ in {None, ""}:
    SCRIPT_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.utils.cli import build_parser, non_negative_float, positive_int  # type: ignore
from scripts.utils.retry import run_with_retry  # type: ignore

CPU_INDEX = "https://download.pytorch.org/whl/cpu"
OPENCLIP_VERSION = "2.24.0"


@dataclass(frozen=True)
class WheelChannel:
    tag: str
    label: str
    index_url: str
    min_cuda: Optional[Tuple[int, int]]


CHANNELS: dict[str, WheelChannel] = {
    "cu124": WheelChannel(tag="cu124", label="CUDA 12.4", index_url="https://download.pytorch.org/whl/cu124", min_cuda=(12, 4)),
    "cu122": WheelChannel(tag="cu122", label="CUDA 12.2", index_url="https://download.pytorch.org/whl/cu122", min_cuda=(12, 2)),
    "cu121": WheelChannel(tag="cu121", label="CUDA 12.1", index_url="https://download.pytorch.org/whl/cu121", min_cuda=(12, 1)),
    "cu118": WheelChannel(tag="cu118", label="CUDA 11.8", index_url="https://download.pytorch.org/whl/cu118", min_cuda=(11, 8)),
    "cpu": WheelChannel(tag="cpu", label="CPU", index_url=CPU_INDEX, min_cuda=None),
}


@dataclass(frozen=True)
class TorchWheelSpec:
    torch_version: str
    torchvision_version: str
    supported_channels: Tuple[str, ...]


TORCH_SPECS: Tuple[TorchWheelSpec, ...] = (
    TorchWheelSpec(torch_version="2.5.1", torchvision_version="0.20.1", supported_channels=("cu124", "cu121", "cpu")),
    TorchWheelSpec(torch_version="2.4.1", torchvision_version="0.19.1", supported_channels=("cu124", "cu121", "cpu")),
    TorchWheelSpec(torch_version="2.3.1", torchvision_version="0.18.1", supported_channels=("cu121", "cu118", "cpu")),
    TorchWheelSpec(torch_version="2.1.2", torchvision_version="0.16.2", supported_channels=("cu118", "cpu")),
)


def run_pip(args: list[str], *, attempts: int, delay: float) -> None:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + args

    def invoke() -> None:
        subprocess.check_call(cmd)

    run_with_retry(invoke, attempts=attempts, delay=delay, exceptions=(subprocess.CalledProcessError,))


def current_variant() -> tuple[Optional[str], Optional[str], bool]:
    try:
        torch = importlib.import_module("torch")
        version = getattr(torch, "__version__", "")
        flavor = None
        if "+" in version:
            flavor = version.split("+", 1)[1]
        has_cuda = torch.cuda.is_available()
        return version, flavor, has_cuda
    except ModuleNotFoundError:
        return None, None, False


def detect_system_cuda_version() -> Optional[Tuple[int, int]]:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        output = subprocess.check_output(["nvidia-smi"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    match = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", output)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def select_cuda_channel(cuda_version: Optional[Tuple[int, int]]) -> Optional[WheelChannel]:
    if not cuda_version:
        return None
    ordered_channels = [CHANNELS["cu124"], CHANNELS["cu122"], CHANNELS["cu121"], CHANNELS["cu118"]]
    for channel in ordered_channels:
        if channel.min_cuda and cuda_version >= channel.min_cuda:
            return channel
    return None


@dataclass
class InstallerConfig:
    desired_build_tag: Optional[str]
    current_version: Optional[str]
    current_flavor: Optional[str]


def needs_install(config: InstallerConfig) -> bool:
    if config.current_version is None:
        return True
    if config.desired_build_tag:
        return config.current_flavor != config.desired_build_tag
    if config.current_flavor and config.current_flavor != "cpu":
        return True
    return False


class InstallationFailed(RuntimeError):
    pass


def iter_specs_for_channel(tag: str) -> list[TorchWheelSpec]:
    return [spec for spec in TORCH_SPECS if tag in spec.supported_channels]


def install_spec(channel: WheelChannel, spec: TorchWheelSpec, *, attempts: int, delay: float) -> None:
    print(
        f"Installing PyTorch ({channel.label}) build "
        f"(torch=={spec.torch_version}, torchvision=={spec.torchvision_version})..."
    )
    run_pip(
        [
            f"--index-url={channel.index_url}",
            f"torch=={spec.torch_version}",
            f"torchvision=={spec.torchvision_version}",
        ],
        attempts=attempts,
        delay=delay,
    )


def install_with_fallback(preferred_tag: Optional[str], *, attempts: int, delay: float) -> None:
    if preferred_tag:
        channel = CHANNELS[preferred_tag]
        try:
            install_best_available(channel, attempts=attempts, delay=delay)
            return
        except InstallationFailed as exc:
            print(f"{exc}. Falling back to CPU build.")
    install_best_available(CHANNELS["cpu"], attempts=attempts, delay=delay)


def install_best_available(channel: WheelChannel, *, attempts: int, delay: float) -> None:
    specs = iter_specs_for_channel(channel.tag)
    if not specs:
        raise InstallationFailed(f"No wheel specs defined for {channel.label}")
    last_error: Optional[subprocess.CalledProcessError] = None
    for spec in specs:
        try:
            install_spec(channel, spec, attempts=attempts, delay=delay)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            print(
                f"PyTorch {spec.torch_version} ({channel.label}) wheel unavailable or failed to install."
                " Trying next compatible release..."
            )
    if last_error:
        raise InstallationFailed(str(last_error))
    raise InstallationFailed(f"Unable to install PyTorch for {channel.label}")


def install_openclip(*, attempts: int, delay: float) -> None:
    print("Installing open-clip-torch...")
    run_pip([f"open-clip-torch=={OPENCLIP_VERSION}", "--no-deps"], attempts=attempts, delay=delay)


def check_cuda_via_subprocess() -> bool:
    cmd = [sys.executable, "-c", "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)"]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


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

    system_cuda = None if args.force_cpu else detect_system_cuda_version()
    desired_channel = None if args.force_cpu else select_cuda_channel(system_cuda)
    if not args.force_cpu and system_cuda and not desired_channel:
        print("Detected CUDA version %s.%s but no matching PyTorch wheel; installing CPU build." % system_cuda)
    version, flavor, has_cuda = current_variant()
    config = InstallerConfig(
        desired_build_tag=desired_channel.tag if desired_channel else None,
        current_version=version,
        current_flavor=flavor,
    )
    pip_kwargs = {"attempts": args.pip_retries, "delay": args.pip_retry_delay}

    if not needs_install(config):
        print(f"Existing PyTorch install ({version}) satisfies requirements.")
        install_openclip(**pip_kwargs)
        return 0

    try:
        install_with_fallback(desired_channel.tag if desired_channel else None, **pip_kwargs)
    except InstallationFailed as exc:
        raise SystemExit(str(exc))

    install_openclip(**pip_kwargs)

    has_cuda_after = check_cuda_via_subprocess()
    if desired_channel and not has_cuda_after:
        print("Warning: PyTorch could not access CUDA; running in CPU mode.")
    else:
        print("PyTorch installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
