import yt_dlp
import random
import os
import requests
import re
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

def format_ytdlp_result(info):
    formats = []
    video_url = audio_url = combined_url = None

    for f in info.get("formats", []):
        url = f.get("url")
        if not url:
            continue

        has_video = f.get("vcodec") not in (None, "none")
        has_audio = f.get("acodec") not in (None, "none")

        if has_video and has_audio:
            combined_url = url
        elif has_video:
            video_url = url
        elif has_audio:
            audio_url = url

        formats.append({
            "url": url,
            "quality": f'{f.get("height") or 720}p',
            "has_video": has_video,
            "has_audio": has_audio,
        })

    # 🌟 استخراج الصورة المصغرة
    thumbnail = info.get("thumbnail", "")
    if not thumbnail or not thumbnail.startswith("http"):
        thumbnails = info.get("thumbnails", [])
        if thumbnails and isinstance(thumbnails, list):
            thumbnail = thumbnails[-1].get("url", "")

    return {
        "title": info.get("title") or "Video",
        "thumbnail": thumbnail,
        "combined_url": combined_url,
        "video_url": video_url or info.get("url"),
        "audio_url": audio_url,
        "formats": formats,
    }


def extract_video_info(url):
    agent = random.choice(USER_AGENTS)

    try:
        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "geo_bypass": True,
            "http_headers": {"User-Agent": agent},
            "impersonate": "chrome", # 🌟 انتحال شخصية المتصفح (بدون بروكسي)
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if info and (info.get("url") or info.get("formats")):
            return format_ytdlp_result(info)

    except Exception as e:
        print(f"yt-dlp failed: {e}")

    raise Exception("فشل .")
