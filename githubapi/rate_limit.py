"""Rate limit handling utilities for GitHub API"""
from dataclasses import dataclass
from datetime import datetime
import requests

@dataclass
class RateLimitInfo:
    remaining: int
    limit: int
    reset_time: datetime
    used: int

    @classmethod
    def from_response(cls, response: requests.Response) -> 'RateLimitInfo':
        headers = response.headers
        return cls(
            remaining=int(headers.get('X-RateLimit-Remaining', 0)),
            limit=int(headers.get('X-RateLimit-Limit', 0)),
            reset_time=datetime.fromtimestamp(int(headers.get('X-RateLimit-Reset', 0))),
            used=int(headers.get('X-RateLimit-Used', 0))
        )

    def is_exceeded(self) -> bool:
        return self.remaining <= 0

    def get_reset_seconds(self) -> int:
        now = datetime.now()
        return max(0, int((self.reset_time - now).total_seconds()))
