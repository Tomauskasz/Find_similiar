from __future__ import annotations

import ssl
from pathlib import Path
from typing import Optional
from urllib import request


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_text(source: str, *, insecure: bool = False, timeout: int = 60) -> str:
    path = Path(source)
    if path.exists():
        return path.read_text(encoding="utf-8")

    context: Optional[ssl.SSLContext] = None
    if insecure:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    with request.urlopen(source, timeout=timeout, context=context) as resp:
        return resp.read().decode("utf-8")


def download_binary(url: str, dest: Path, *, timeout: int = 60) -> Path:
    """
    Download the resource at `url` to `dest`. Raises RuntimeError if the request fails.
    """
    ensure_directory(dest.parent)
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return dest
    except Exception as exc:
        raise RuntimeError(f"failed to download {url}") from exc
