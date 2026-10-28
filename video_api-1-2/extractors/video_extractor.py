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
    
    seen_qualities = set()
    audio_added = False

    for f in info.get("formats", []):
        url = f.get("url")
        if not url:
            continue

        height = f.get("height")
        has_video = f.get("vcodec") not in (None, "none")
        has_audio = f.get("acodec") not in (None, "none")

        # 1. تصفية الفيديو ليقتصر بدقة على 720p و 480p فقط (من غير صوت أو مع صوت)
        if has_video:
            if height in [720, 480]:
                quality_str = f"{height}p"
                if quality_str not in seen_qualities:
                    seen_qualities.add(quality_str)
                    formats.append({
                        "url": url,
                        "quality": quality_str,
                        "has_video": True,
                        "has_audio": has_audio,
                    })
                    if has_audio:
                        combined_url = url
                    else:
                        video_url = url
        
        # 2. جعل الصوت يظهر بصيغة واحدة فقط وعدم تكراره
        elif has_audio and not has_video:
            if not audio_added:
                audio_added = True
                audio_url = url
                formats.append({
                    "url": url,
                    "quality": "Standard Audio",
                    "has_video": False,
                    "has_audio": True,
                })

    thumbnail = info.get("thumbnail", "")
    if not thumbnail or not thumbnail.startswith("http"):
        thumbnails = info.get("thumbnails", [])
        if thumbnails and isinstance(thumbnails, list):
            thumbnail = thumbnails[-1].get("url", "")

    return {
        "title": info.get("title") or "Video",
        "thumbnail": thumbnail,
        "combined_url": combined_url,
        "video_url": video_url or combined_url,
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
                    "quality": "720p",
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

        og_image = ""
        meta_img = soup.find("meta", property="og:image")
        if meta_img and meta_img.get("content"):
            og_image = meta_img.get("content")

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
                "thumbnail": og_image,
                "combined_url": direct_url,
                "video_url": direct_url,
                "audio_url": None,
                "formats": [{
                    "url": direct_url,
                    "quality": "720p",
                    "has_video": True,
                    "has_audio": True,
                }],
            }
    except Exception as e:
        print(f"Direct extraction failed: {e}")

    raise Exception("No quality options available.")
