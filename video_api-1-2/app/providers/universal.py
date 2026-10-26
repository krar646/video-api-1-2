"""Universal provider implementation using yt-dlp for social media."""

import os
import re
import json
import requests
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

SUPPORTED_DOMAINS = [
    "instagram.com", "facebook.com", "fb.watch", "tiktok.com",
    "twitter.com", "x.com", "snapchat.com", "reddit.com",
    "vimeo.com", "dailymotion.com", "pinterest.com"
]

class UniversalProvider(VideoProvider):
    def __init__(self, config: Dict, cookie_service: Optional[Any] = None):
        self.config = config
        self.cookie_service = cookie_service
        
        # مسار الكوكيز المباشر
        self.cookie_path: Optional[str] = "/opt/render/project/src/cookies.txt"
        if not os.path.isfile(self.cookie_path):
            self.cookie_path = config.get("cookie_path")

        # إعدادات yt-dlp
        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "geo_bypass": True,
            "impersonate": "chrome",
            "extractor_retries": 3,
            "socket_timeout": 15,
        }

        if self.cookie_path and os.path.isfile(self.cookie_path):
            self.base_opts["cookiefile"] = self.cookie_path
            logger.info(f"✅ Cookie file loaded from: {self.cookie_path}")
        else:
            logger.warning(f"⚠️ No cookie file found at: {self.cookie_path}")

    def validate_url(self, url: str) -> bool:
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return False
        return any(domain in url_lower for domain in SUPPORTED_DOMAINS)

    async def get_info(self, url: str, include_formats: bool = False, include_subtitles: bool = False) -> Dict:
        if not self.validate_url(url):
            if "youtube" in url.lower():
                raise InvalidURLError("لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل.")
            raise InvalidURLError("الرابط غير مدعوم.")

        # المحاولة الأساسية بـ yt-dlp
        try:
            with yt_dlp.YoutubeDL(self.base_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info:
                result = {
                    "video_id": info.get("id", ""),
                    "title": info.get("title", "فيديو"),
                    "duration": info.get("duration", 0),
                    "author": info.get("uploader", ""),
                    "upload_date": info.get("upload_date", ""),
                    "view_count": info.get("view_count", 0),
                    "thumbnail_url": info.get("thumbnail", ""),
                    "description": info.get("description", ""),
                }
                if include_formats:
                    result["formats"] = self._extract_formats(info)
                return result
        except Exception as e:
            logger.warning(f"yt-dlp failed: {e}. Trying manual extraction...")

        # الخطة البديلة (لو yt-dlp فشل)
        return await self._manual_extract(url, include_formats)

    async def _manual_extract(self, url: str, include_formats: bool) -> Dict:
        """الخطة ب: استخراج الفيديو من صفحة الويب مباشرة"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text

            # استخراج العنوان والصورة
            title = "فيديو"
            thumbnail = ""
            title_match = re.search(r'<meta property="og:title" content="(.*?)"', html)
            if title_match:
                title = title_match.group(1)

            thumb_match = re.search(r'<meta property="og:image" content="(.*?)"', html)
            if thumb_match:
                thumbnail = thumb_match.group(1).replace('&amp;', '&')

            # البحث عن روابط الفيديو
            video_urls = re.findall(r'"(https:\\/\\/[^"]+?\.mp4[^"]*)"', html)
            video_urls += re.findall(r'"(https:[^"]+?\.mp4[^"]*)"', html)

            if not video_urls:
                raise VideoUnavailableError("لم يتم العثور على روابط فيديو في الصفحة.")

            # تنظيف الروابط
            cleaned_urls = []
            for v_url in video_urls:
                v_url = v_url.replace('\\/', '/').replace('\\u0025', '%')
                if v_url not in cleaned_urls:
                    cleaned_urls.append(v_url)

            formats = []
            for i, v_url in enumerate(cleaned_urls):
                formats.append({
                    "format_id": f"manual_{i}",
                    "ext": "mp4",
                    "resolution": "HD",
                    "audio_bitrate": None,
                    "video_codec": None,
                    "audio_codec": None,
                    "filesize": None,
                    "format_type": "video+audio",
                    "url": v_url,
                })

            return {
                "video_id": "manual",
                "title": title,
                "duration": 0,
                "author": "",
                "upload_date": "",
                "view_count": 0,
                "thumbnail_url": thumbnail,
                "description": "",
                "formats": formats if include_formats else [],
            }

        except Exception as e:
            logger.error(f"Manual extraction failed: {e}")
            raise ProviderError(f"فشل في استخراج الفيديو: {e}")

    def _extract_formats(self, info: Dict) -> List[Dict]:
        formats = []
        for f in info.get("formats", []):
            if not f.get("url"):
                continue
            has_video = f.get("vcodec") != "none" and f.get("vcodec") is not None
            has_audio = f.get("acodec") != "none" and f.get("acodec") is not None
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
                "url": f.get("url"),
            })
        return formats

    async def list_formats(self, url: str) -> List[VideoFormat]:
        info = await self.get_info(url, include_formats=True)
        formats = []
        for f in info.get("formats", []):
            formats.append(VideoFormat(
                format_id=f["format_id"], ext=f["ext"], resolution=f["resolution"],
                audio_bitrate=f["audio_bitrate"], video_codec=f["video_codec"],
                audio_codec=f["audio_codec"], filesize=f["filesize"],
                format_type=f["format_type"]
            ))
        return formats

    async def download(
        self, url: str, format_id: Optional[str] = None,
        output_template: Optional[str] = None, extract_audio: bool = False,
        audio_format: Optional[str] = None, include_subtitles: bool = False,
        subtitle_lang: Optional[str] = None
    ) -> DownloadResult:
        info = await self.get_info(url, include_formats=True)
        direct_url = ""
        selected_format = None
        formats = info.get("formats", [])

        if extract_audio:
            for f in formats:
                if f["format_type"] == "audio-only":
                    direct_url = f["url"]
                    selected_format = f["format_id"]
                    break
        else:
            for f in reversed(formats):
                if f["format_type"] == "video+audio":
                    direct_url = f["url"]
                    selected_format = f["format_id"]
                    break
            if not direct_url:
                for f in reversed(formats):
                    if f["format_type"] == "video-only":
                        direct_url = f["url"]
                        selected_format = f["format_id"]
                        break
        if not direct_url:
            raise VideoUnavailableError("لم يتم العثور على رابط تحميل صالح.")
        return DownloadResult(
            file_path=direct_url, file_size=0, duration=info.get("duration", 0),
            format_id=selected_format or "best"
        )

    def get_cookie_path(self) -> Optional[str]:
        return self.cookie_path
