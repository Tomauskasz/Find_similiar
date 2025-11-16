#!/usr/bin/env python
"""Download a sample of images from the PASS dataset into data/catalog."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable
from urllib import request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

PASS_URL_LIST = "https://www.robots.ox.ac.uk/~vgg/research/pass/pass_urls.txt"


def fetch_url_list(source: str, insecure: bool = False) -> list[str]:
    if Path(source).exists():
        text = Path(source).read_text(encoding="utf-8")
    else:
        context = None
        if insecure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        with request.urlopen(source, timeout=60, context=context) as resp:
            text = resp.read().decode("utf-8")
    urls = [line.strip() for line in text.splitlines() if line.strip()]
    if not urls:
        raise RuntimeError("No URLs found in PASS list.")
    return urls


def iter_target_paths(out_dir: Path, prefix: str = "pass") -> Iterable[Path]:
    existing = sorted(out_dir.glob(f"{prefix}_*.jpg"))
    start_idx = 0
    if existing:
        last = existing[-1].stem
        try:
            start_idx = int(last.split("_")[1]) + 1
        except Exception:
            start_idx = len(existing)
    idx = start_idx
    while True:
        yield out_dir / f"{prefix}_{idx:06d}.jpg"
        idx += 1


def download_image(url: str, dest: Path, timeout: int = 60) -> bool:
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        print(f"[warn] failed to download {url}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download images from the PASS dataset into the catalog."
    )
    parser.add_argument("--count", type=int, default=500, help="Number of images to download")
    parser.add_argument(
        "--urls",
        type=str,
        default=PASS_URL_LIST,
        help="PASS URL list (remote URL or local file)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/catalog"),
        help="Destination directory for images",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling URLs",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate validation when downloading pass_urls.txt",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel download workers (default: 8)",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    urls = fetch_url_list(args.urls, insecure=args.insecure)
    random.Random(args.seed).shuffle(urls)
    selected = urls[: args.count]

    target_iter = iter_target_paths(args.out, prefix="pass")
    targets = [next(target_iter) for _ in selected]

    print(f"Downloading {len(selected)} PASS images with {args.workers} workers...")
    successes = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_url = {
            executor.submit(download_image, url, dest): (url, dest)
            for url, dest in zip(selected, targets)
        }
        for future in as_completed(future_to_url):
            url, _ = future_to_url[future]
            try:
                if future.result():
                    successes += 1
            except Exception as exc:
                print(f"[error] download failed for {url}: {exc}")

    print(f"Downloaded {successes}/{args.count} PASS images to {args.out}")

    return 0 if successes == args.count else 1


if __name__ == "__main__":
    raise SystemExit(main())
