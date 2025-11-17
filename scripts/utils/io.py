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


def download_binary(url: str, dest: Path, *, timeout: int = 60) -> bool:
    try:
        ensure_directory(dest.parent)
        with request.urlopen(url, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        print(f"[warn] failed to download {url}: {exc}")
        return False
