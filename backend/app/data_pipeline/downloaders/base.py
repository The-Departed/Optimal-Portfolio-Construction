"""Shared download infrastructure."""

import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import requests


class DownloadError(RuntimeError):
    """A source could not be retrieved or returned an unusable response."""


@dataclass
class DownloadContext:
    start: date
    end: date
    timeout_seconds: float
    pause_seconds: float
    user_agent: str
    # Per-run cache so one HTTP response can serve several datasets (e.g. one AMFI
    # fund-house file contains both ETF schemes).
    cache: dict[Any, Any] = field(default_factory=dict)
    _session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers["User-Agent"] = self.user_agent
        return self._session

    def pause(self) -> None:
        if self.pause_seconds > 0:
            time.sleep(self.pause_seconds)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def checked_get(ctx: DownloadContext, url: str, **kwargs: Any) -> requests.Response:
    return _checked(ctx, "GET", url, **kwargs)


def checked_post(ctx: DownloadContext, url: str, **kwargs: Any) -> requests.Response:
    return _checked(ctx, "POST", url, **kwargs)


def _checked(ctx: DownloadContext, method: str, url: str, **kwargs: Any) -> requests.Response:
    try:
        response = ctx.session.request(method, url, timeout=ctx.timeout_seconds, **kwargs)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"{method} {url} failed: {exc}") from exc
    return response
