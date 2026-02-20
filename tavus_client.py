"""
Tavus API client for creating and polling avatar videos.
"""
import logging
import time
from dataclasses import dataclass
from typing import Generator, Optional

import requests

from config import AppConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class VideoCreateResult:
    """Result of requesting video creation."""

    video_id: str
    status_url: str
    error: Optional[str] = None


@dataclass
class VideoStatusResult:
    """Result of a video status check."""

    status: str  # queued, generating, ready, error, deleted
    download_url: Optional[str] = None
    status_details: Optional[str] = None


class TavusClient:
    """Client for Tavus video generation API."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or get_config()
        self._tavus = self._config.tavus
        self._session = requests.Session()
        self._session.headers.update(
            {"x-api-key": self._tavus.api_key, "Content-Type": "application/json"}
        )

    def create_video(self, script: str) -> VideoCreateResult:
        """
        Request video generation. Returns video_id and status_url on success,
        or error message in result.error.
        """
        script = (script or "").strip()
        if not script:
            return VideoCreateResult(
                video_id="",
                status_url="",
                error="Script is empty",
            )
        if not self._tavus.replica_id:
            return VideoCreateResult(
                video_id="",
                status_url="",
                error="TAVUS_REPLICA_ID is not set",
            )

        url = self._tavus.videos_url
        payload = {"replica_id": self._tavus.replica_id, "script": script}
        timeout = self._tavus.request_timeout_seconds

        try:
            response = self._session.post(
                url, json=payload, timeout=timeout
            )
        except requests.RequestException as e:
            logger.exception("Tavus create request failed")
            return VideoCreateResult(
                video_id="", status_url="", error=str(e)
            )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if not response.ok:
            msg = (
                data.get("error")
                or data.get("message")
                or response.reason
                or f"HTTP {response.status_code}"
            )
            logger.warning("Tavus API error: %s", msg)
            return VideoCreateResult(video_id="", status_url="", error=msg)

        if data.get("status") != "queued":
            msg = (
                data.get("error")
                or data.get("message")
                or f"Unexpected status: {data.get('status')}"
            )
            logger.warning("Video not queued: %s", msg)
            return VideoCreateResult(video_id="", status_url="", error=msg)

        video_id = data.get("video_id")
        if not video_id:
            return VideoCreateResult(
                video_id="", status_url="", error="No video_id in response"
            )

        status_url = f"{self._tavus.videos_url}/{video_id}"
        logger.info("Video queued: %s", video_id)
        return VideoCreateResult(video_id=video_id, status_url=status_url)

    def get_status(self, status_url: str) -> VideoStatusResult:
        """Fetch current video status."""
        try:
            response = self._session.get(
                status_url, timeout=self._tavus.request_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning("Status check failed: %s", e)
            return VideoStatusResult(
                status="error",
                status_details=str(e),
            )
        except ValueError:
            return VideoStatusResult(status="error", status_details="Invalid JSON")

        return VideoStatusResult(
            status=data.get("status", "unknown"),
            download_url=data.get("download_url"),
            status_details=data.get("status_details"),
        )

    def wait_for_video(
        self,
        status_url: str,
        poll_interval: Optional[int] = None,
        max_wait: Optional[int] = None,
    ) -> Generator[VideoStatusResult, None, None]:
        """
        Poll status until ready, error, or timeout. Yields after each poll.
        """
        interval = poll_interval or self._tavus.poll_interval_seconds
        deadline = time.monotonic() + (max_wait or self._tavus.poll_max_wait_seconds)

        while time.monotonic() < deadline:
            result = self.get_status(status_url)
            yield result
            if result.status == "ready":
                return
            if result.status in ("error", "deleted"):
                return
            time.sleep(interval)

        yield VideoStatusResult(
            status="timeout",
            status_details="Video generation timed out.",
        )
