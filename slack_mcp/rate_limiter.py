import threading
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta

class SlackRateLimiter:
    """
    Tracks Slack API rate limits per method, queues requests, and provides ETA for next available call.
    Thread-safe for use in production and testing.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.next_allowed: Dict[str, float] = {}  # method -> unix timestamp
        self.queue: Dict[str, list] = {}  # method -> list of (callable, args, kwargs, callback)

    def is_rate_limited(self, method: str) -> Optional[float]:
        """
        Returns seconds to wait if rate limited, else None.
        """
        with self.lock:
            now = time.time()
            if method in self.next_allowed and now < self.next_allowed[method]:
                return self.next_allowed[method] - now
            return None

    def set_rate_limit(self, method: str, retry_after: float):
        """
        Sets the next allowed time for a method.
        """
        with self.lock:
            self.next_allowed[method] = time.time() + retry_after

    def get_eta(self, method: str) -> Optional[str]:
        with self.lock:
            ts = self.next_allowed.get(method)
            if ts and ts > time.time():
                return datetime.fromtimestamp(ts).isoformat()
            return None

    def wrap(self, method: str, func: Callable, *args, **kwargs) -> Any:
        """
        Call the Slack API method with rate limit handling.
        If rate limited, returns a dict with ETA and message.
        """
        wait = self.is_rate_limited(method)
        if wait:
            eta = self.get_eta(method)
            return {
                "error": "ratelimited",
                "retry_after": round(wait),
                "eta": eta,
                "message": f"Rate limit hit for {method}. Waiting {round(wait)} seconds. ETA: {eta}."
            }
        try:
            result = func(*args, **kwargs)
            # If Slack returns a 429 error, handle it below
            if isinstance(result, dict) and result.get("error") == "ratelimited":
                retry_after = result.get("retry_after") or 30  # fallback to 30s if not provided
                self.set_rate_limit(method, float(retry_after))
                eta = self.get_eta(method)
                return {
                    "error": "ratelimited",
                    "retry_after": round(float(retry_after)),
                    "eta": eta,
                    "message": f"Rate limit hit for {method}. Waiting {round(float(retry_after))} seconds. ETA: {eta}."
                }
            return result
        except Exception as e:
            # If it's a SlackApiError with 429, extract Retry-After
            if hasattr(e, "response") and hasattr(e.response, "status_code") and e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 30))
                self.set_rate_limit(method, retry_after)
                eta = self.get_eta(method)
                return {
                    "error": "ratelimited",
                    "retry_after": retry_after,
                    "eta": eta,
                    "message": f"Rate limit hit for {method}. Waiting {retry_after} seconds. ETA: {eta}."
                }
            raise
