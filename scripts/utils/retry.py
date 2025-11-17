from __future__ import annotations

import time
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


def run_with_retry(
    func: Callable[[], T],
    *,
    attempts: int = 3,
    delay: float = 1.0,
    exceptions: Sequence[type[BaseException]] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """
    Execute `func`, retrying on failure up to `attempts` times with a fixed delay.
    Raises the last exception if all attempts fail.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if delay < 0:
        raise ValueError("delay must be >= 0")

    for attempt in range(1, attempts + 1):
        try:
            return func()
        except tuple(exceptions) as exc:
            if attempt >= attempts:
                raise
            if on_retry:
                on_retry(attempt, exc)
            if delay:
                time.sleep(delay)

    # This should never be reached because the loop either returns or raises.
    raise RuntimeError("run_with_retry exhausted attempts without returning")
