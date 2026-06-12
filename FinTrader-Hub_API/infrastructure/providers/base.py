import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


def request_with_retries(
    request_fn: Callable[[], httpx.Response],
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
) -> httpx.Response:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = request_fn()
            if response.status_code == 429:
                raise httpx.HTTPStatusError(
                    "Rate limit exceeded",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                delay = base_delay_seconds * (2**attempt)
                logger.warning("Provider request failed (attempt %s): %s", attempt + 1, exc)
                time.sleep(delay)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Provider request failed without exception")
