"""YouTube provider implementation (Blocked / Restricted)."""

import os
import structlog

from app.models.video import DownloadResult, VideoFormat
from app.providers.base import VideoProvider
from app.providers.exceptions import InvalidURLError

logger = structlog.get_logger(__name__)


def _is_test_mode() -> bool:
    """Check if test mode is enabled via environment variable."""
    return os.environ.get("APP_TESTING_TEST_MODE", "").lower() in ("true", "1", "yes")


class YouTubeProvider(VideoProvider):
    """YouTube video provider implementation (Blocked)."""

    def __init__(self, config: dict, cookie_service: Optional[Any] = None):
        self.config = config
        self.cookie_path: str = config.get("cookie_path") or "/app/cookies/youtube.txt"
        self._test_mode = _is_test_mode()
        logger.info("YouTube provider initialized in blocked mode")

    def validate_url(self, url: str) -> bool:
        """Always return False for YouTube URLs to block them."""
        return False

    def extract_video_id(self, url: str) -> Optional[str]:
        return None

    async def get_info(
        self, url: str, include_formats: bool = False, include_subtitles: bool = False
    ) -> dict:
        raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")

    async def list_formats(self, url: str) -> list[VideoFormat]:
        raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")

    async def get_transcript(self, url: str, lang: str = "en", source: str = "any") -> dict:
        raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")

    async def download(
        self,
        url: str,
        format_id: Optional[str] = None,
        output_template: Optional[str] = None,
        extract_audio: bool = False,
        audio_format: Optional[str] = None,
        include_subtitles: bool = False,
        subtitle_lang: Optional[str] = None,
    ) -> DownloadResult:
        raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")

    def get_cookie_path(self) -> Optional[str]:
        return self.cookie_path