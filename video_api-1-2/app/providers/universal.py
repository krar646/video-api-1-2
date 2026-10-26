"""Universal provider implementation using yt-dlp for social media.

This provider is designed to handle video extraction for a wide range
of platforms (Instagram, Facebook, TikTok, Twitter, etc.) except YouTube.
It features robust error handling, format filtering, and cookie support.
"""

import os
from typing import Any, Dict, List, Optional

import structlog
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, UnsupportedError

from app.models.video import DownloadResult, VideoFormat
from app.providers.base import VideoProvider
from app.providers.exceptions import (
    InvalidURLError,
    ProviderError,
    VideoUnavailableError,
)

logger = structlog.get_logger(__name__)

# Supported domains (used for validation)
SUPPORTED_DOMAINS = [
    "instagram.com", "facebook.com", "fb.watch", "tiktok.com",
    "twitter.com", "x.com", "snapchat.com", "reddit.com",
    "vimeo.com", "dailymotion.com", "pinterest.com"
]

class UniversalProvider(VideoProvider):
    """Universal provider for non-YouTube social media using yt-dlp."""

    def __init__(self, config: Dict, cookie_service: Optional[Any] = None):
        self.config = config
        self.cookie_service = cookie_service
        self.cookie_path: Optional[str] = config.get("cookie_path")

        # 🌟 إعدادات yt-dlp الأساسية
        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "geo_bypass": True,
            "impersonate": "chrome",  # تخطي حماية المواقع
            "extractor_retries": 3,   # إعادة المحاولة عند الفشل
            "socket_timeout": 15,     # مهلة الاتصال
        }

        if self.cookie_path and os.path.isfile(self.cookie_path):
            self.base_opts["cookiefile"] = self.cookie_path
            logger.info("Cookie file loaded for Universal Provider")
        else:
            logger.warning("No cookie file found. Extraction may fail for some sites.")

    def validate_url(self, url: str) -> bool:
        """Block YouTube and validate against supported domains."""
        url_lower = url.lower()

        # 🌟 استثناء صارم ليوتيوب
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return False

        # 🌟 التحقق من أن الرابط ينتمي لموقع مدعوم
        return any(domain in url_lower for domain in SUPPORTED_DOMAINS)

    async def get_info(
        self, url: str, include_formats: bool = False, include_subtitles: bool = False
    ) -> Dict:
        """Extract video metadata with robust error handling."""

        if not self.validate_url(url):
            if "youtube" in url.lower():
                raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")
            raise InvalidURLError("الرابط غير مدعوم.")

        try:
            with yt_dlp.YoutubeDL(self.base_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise VideoUnavailableError("لم يتم العثور على بيانات الفيديو.")

            # تجهيز البيانات الأساسية
            result = {
                "video_id": info.get("id", ""),
                "title": info.get("title", "فيديو بدون عنوان"),
                "duration": info.get("duration", 0),
                "author": info.get("uploader", "غير معروف"),
                "upload_date": info.get("upload_date", ""),
                "view_count": info.get("view_count", 0),
                "thumbnail_url": info.get("thumbnail", ""),
                "description": info.get("description", ""),
            }

            # 🌟 استخراج الجودات وتصنيفها
            if include_formats:
                result["formats"] = self._extract_formats(info)

            return result

        except UnsupportedError as e:
            logger.error(f"Unsupported URL: {url} - {e}")
            raise InvalidURLError("هذا الموقع غير مدعوم حالياً.")
        except ExtractorError as e:
            logger.error(f"Extractor error: {url} - {e}")
            raise VideoUnavailableError(f"فشل في استخراج البيانات: {e}")
        except DownloadError as e:
            logger.error(f"Download error: {url} - {e}")
            raise ProviderError(f"خطأ في السيرفر: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {url} - {e}")
            raise ProviderError("حدث خطأ غير متوقع أثناء معالجة الفيديو.")

    def _extract_formats(self, info: Dict) -> List[Dict]:
        """Extract and format available streams."""
        formats = []
        for f in info.get("formats", []):
            if not f.get("url"):
                continue

            has_video = f.get("vcodec") != "none" and f.get("vcodec") is not None
            has_audio = f.get("acodec") != "none" and f.get("acodec") is not None

            # تجاهل الجودات اللي مش فيها صوت ولا فيديو
            if not has_video and not has_audio:
                continue

            format_type = "video+audio"
            if has_video and not has_audio:
                format_type = "video-only"
            elif has_audio and not has_video:
                format_type = "audio-only"

            formats.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
                "audio_bitrate": f.get("abr"),
                "video_codec": f.get("vcodec"),
                "audio_codec": f.get("acodec"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "format_type": format_type,
                "url": f.get("url"),  # نحتفظ بالرابط المباشر
            })
        return formats

    async def list_formats(self, url: str) -> List[VideoFormat]:
        """List all available formats for a video."""
        info = await self.get_info(url, include_formats=True)
        formats = []

        for f in info.get("formats", []):
            formats.append(VideoFormat(
                format_id=f["format_id"],
                ext=f["ext"],
                resolution=f["resolution"],
                audio_bitrate=f["audio_bitrate"],
                video_codec=f["video_codec"],
                audio_codec=f["audio_codec"],
                filesize=f["filesize"],
                format_type=f["format_type"]
            ))
        return formats

    async def download(
        self, url: str, format_id: Optional[str] = None,
        output_template: Optional[str] = None, extract_audio: bool = False,
        audio_format: Optional[str] = None, include_subtitles: bool = False,
        subtitle_lang: Optional[str] = None
    ) -> DownloadResult:
        """
        In this architecture, the actual downloading is handled by the DownloadWorker.
        This method returns the direct URL and metadata.
        """
        info = await self.get_info(url, include_formats=True)

        direct_url = ""
        selected_format = None

        # 🌟 اختيار أفضل جودة متاحة بناءً على الطلب
        formats = info.get("formats", [])

        # لو الطلب صوتيات
        if extract_audio:
            for f in formats:
                if f["format_type"] == "audio-only":
                    direct_url = f["url"]
                    selected_format = f["format_id"]
                    break
        # لو الطلب فيديو
        else:
            # نبحث عن فيديو+صوت أولاً (لأنه الأفضل)
            for f in reversed(formats):
                if f["format_type"] == "video+audio":
                    direct_url = f["url"]
                    selected_format = f["format_id"]
                    break

            # لو مفيش فيديو+صوت، نجيب أفضل فيديو (هيحتاج دمج في التطبيق)
            if not direct_url:
                for f in reversed(formats):
                    if f["format_type"] == "video-only":
                        direct_url = f["url"]
                        selected_format = f["format_id"]
                        break

        if not direct_url:
            raise VideoUnavailableError("لم يتم العثور على رابط تحميل صالح.")

        return DownloadResult(
            file_path=direct_url,
            file_size=0,
            duration=info.get("duration", 0),
            format_id=selected_format or "best"
        )

    def get_cookie_path(self) -> Optional[str]:
        return self.cookie_path