import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException

_buckets: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(
    key: str,
    max_calls: int,
    window_sec: int,
    label: str = "requests",
) -> None:
    now = time.time()
    cutoff = now - window_sec
    recent = [t for t in _buckets[key] if t > cutoff]

    if len(recent) >= max_calls:
        retry_after = max(1, int(window_sec - (now - recent[0])))
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many {label}. Limit is {max_calls} per "
                f"{window_sec // 60} minutes. Try again in {retry_after}s."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    recent.append(now)
    _buckets[key] = recent
