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

    return {
        "title": info.get("title") or "Video",
        "thumbnail": info.get("thumbnail", ""),
        "combined_url": combined_url,
        "video_url": video_url or info.get("url"),
        "audio_url": audio_url,
        "formats": formats,
    }


def extract_video_info(url):
    agent = random.choice(USER_AGENTS)
    cookies = os.path.join(os.path.dirname(__file__), "..", "cookies.txt")

    for use_cookies in (True, False):
        try:
            options = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
                "geo_bypass": True,
                "http_headers": {"User-Agent": agent},
            }

            if use_cookies and os.path.isfile(cookies):
                options["cookiefile"] = cookies

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            if info and (info.get("url") or info.get("formats")):
                return format_ytdlp_result(info)

        except Exception as e:
            print(f"yt-dlp failed: {e}")

    try:
        import streamlink

        streams = streamlink.streams(url)
        stream = streams.get("best") or next(iter(streams.values()), None)

        if stream:
            stream_url = stream.url
            return {
                "title": "Video Stream",
                "thumbnail": "",
                "combined_url": stream_url,
                "video_url": stream_url,
                "audio_url": None,
                "formats": [{
                    "url": stream_url,
                    "quality": "HD",
                    "has_video": True,
                    "has_audio": True,
                }],
            }
    except Exception as e:
        print(f"Streamlink failed: {e}")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": agent, "Referer": url},
            timeout=10,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        urls = [
            tag.get("src")
            for tag in soup.find_all(["video", "source"])
            if tag.get("src") and tag.get("src").startswith("http")
        ]

        urls += re.findall(
            r'https?://[^\s<>"]+?\.(?:mp4|m3u8|webm)',
            response.text,
        )

        if urls:
            direct_url = urls[0]
            title = soup.title.get_text(strip=True) if soup.title else "Video"

            return {
                "title": title,
                "thumbnail": "",
                "combined_url": direct_url,
                "video_url": direct_url,
                "audio_url": None,
                "formats": [{
                    "url": direct_url,
                    "quality": "HD",
                    "has_video": True,
                    "has_audio": True,
                }],
            }
    except Exception as e:
        print(f"Direct extraction failed: {e}")

    raise Exception("No quality options available.")
