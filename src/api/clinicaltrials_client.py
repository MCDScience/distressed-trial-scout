from __future__ import annotations

import logging
import time
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import (
    API_PAGE_SIZE_MAX,
    API_THROTTLE_SECONDS,
    CTGOV_API_BASE,
    CTGOV_FIELDS,
    DISTRESSED_STATUSES,
)

logger = logging.getLogger(__name__)


class ClinicalTrialsClient:
    """ClinicalTrials.gov API v2 client with pagination and throttling."""

    def __init__(self, throttle_seconds: float = API_THROTTLE_SECONDS) -> None:
        self.throttle_seconds = throttle_seconds
        self._last_request_at: float | None = None
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "DistressedTrialScout/0.1 (research; mailto:local)"}
        )

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.throttle_seconds:
            time.sleep(self.throttle_seconds - elapsed)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get_page(self, params: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        response = self._session.get(CTGOV_API_BASE, params=params, timeout=60)
        response.raise_for_status()
        self._last_request_at = time.monotonic()
        return response.json()

    def fetch_studies(
        self,
        condition: str,
        max_count: int,
        statuses: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch up to max_count studies matching condition and distressed statuses."""
        if max_count <= 0:
            return []

        status_filter = statuses or DISTRESSED_STATUSES
        collected: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(collected) < max_count:
            remaining = max_count - len(collected)
            page_size = min(remaining, API_PAGE_SIZE_MAX)
            params: dict[str, Any] = {
                "query.cond": condition,
                "filter.overallStatus": ",".join(status_filter),
                "sort": "LastUpdatePostDate:desc",
                "pageSize": page_size,
                "fields": ",".join(CTGOV_FIELDS),
            }
            if page_token:
                params["pageToken"] = page_token

            payload = self._get_page(params)
            studies = payload.get("studies") or []
            if not studies:
                break

            collected.extend(studies)
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return collected[:max_count]
