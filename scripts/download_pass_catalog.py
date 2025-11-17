#!/usr/bin/env python
"""Download a sample of images from the PASS dataset into data/catalog."""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from .utils.cli import (
    build_parser,
    non_negative_float,
    non_negative_int,
    positive_int,
)
from .utils.io import download_binary, ensure_directory, fetch_text
from .utils.retry import run_with_retry

PASS_URL_LIST = "https://www.robots.ox.ac.uk/~vgg/research/pass/pass_urls.txt"


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


def main() -> int:
    parser = build_parser("Download images from the PASS dataset into the catalog.")
    parser.add_argument("--count", type=positive_int, default=500, help="Number of images to download")
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
    parser.add_argument("--seed", type=non_negative_int, default=42, help="Random seed for sampling URLs")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate validation when downloading pass_urls.txt",
    )
    parser.add_argument("--workers", type=positive_int, default=8, help="Parallel download workers")
    parser.add_argument(
        "--retry-attempts",
        type=positive_int,
        default=3,
        help="Retry attempts for fetching metadata and individual downloads.",
    )
    parser.add_argument(
        "--retry-delay",
        type=non_negative_float,
        default=1.5,
        help="Seconds to wait between retries (0 disables the delay).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the files that would be downloaded without fetching them.",
    )
    args = parser.parse_args()

    ensure_directory(args.out)

    text = run_with_retry(
        lambda: fetch_text(args.urls, insecure=args.insecure),
        attempts=args.retry_attempts,
        delay=args.retry_delay,
    )
    urls = [line.strip() for line in text.splitlines() if line.strip()]
    if not urls:
        raise RuntimeError("No URLs found in PASS list.")
    random.Random(args.seed).shuffle(urls)
    selected = urls[: args.count]

    target_iter = iter_target_paths(args.out, prefix="pass")
    targets = [next(target_iter) for _ in selected]

    if args.dry_run:
        print("Dry run: the following downloads would be scheduled:")
        for url, dest in zip(selected, targets):
            print(f"  {url} -> {dest}")
        return 0

    print(f"Downloading {len(selected)} PASS images with {args.workers} workers...")
    successes = 0

    def download_with_retry(url: str, dest: Path) -> None:
        return run_with_retry(
            lambda: download_binary(url, dest, timeout=60),
            attempts=args.retry_attempts,
            delay=args.retry_delay,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_url = {
            executor.submit(download_with_retry, url, dest): (url, dest)
            for url, dest in zip(selected, targets)
        }
        for future in as_completed(future_to_url):
            url, _ = future_to_url[future]
            try:
                future.result()
                successes += 1
            except Exception as exc:
                print(f"[error] download failed for {url}: {exc}")

    print(f"Downloaded {successes}/{args.count} PASS images to {args.out}")

    return 0 if successes == args.count else 1


if __name__ == "__main__":
    raise SystemExit(main())
