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
    combined_url = None
    video_url = None
    audio_url = None

    seen_qualities = set()
    audio_added = False

    for f in info.get("formats", []):
        url = f.get("url")
        if not url:
            continue

        height = f.get("height")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        
        has_video = vcodec not in (None, "none")
        has_audio = acodec not in (None, "none")

        if has_video and height:
            if height >= 720:
                q_str = "720p"
            elif height >= 480:
                q_str = "480p"
            else:
                q_str = f"{height}p"

            if q_str not in seen_qualities and q_str in ["720p", "480p"]:
                seen_qualities.add(q_str)
                formats.append({
                    "url": url,
                    "quality": q_str,
                    "has_video": True,
                    "has_audio": has_audio,
                })
                if has_audio and not combined_url:
                    combined_url = url
                elif not video_url:
                    video_url = url

        if has_audio and not has_video:
            if not audio_added:
                audio_added = True
                audio_url = url
                formats.append({
                    "url": url,
                    "quality": "audio_fast",
                    "has_video": False,
                    "has_audio": True,
                })

    if not formats and info.get("url"):
        fallback_url = info.get("url")
        formats.append({
            "url": fallback_url,
            "quality": "720p",
            "has_video": True,
            "has_audio": True,
        })
        combined_url = fallback_url

    thumbnail = info.get("thumbnail", "")
    if not thumbnail or not thumbnail.startswith("http"):
        thumbnails = info.get("thumbnails", [])
        if thumbnails and isinstance(thumbnails, list):
            thumbnail = thumbnails[-1].get("url", "")

    # 🌟 استخراج اسم صاحب الحساب أو القناة بدقة كاسم أساسي للفيديو
    uploader_name = (
        info.get("uploader") or 
        info.get("channel") or 
        info.get("creator") or 
        info.get("uploader_id")
    )
    
    video_title = info.get("title") or "Video"
    
    if uploader_name:
        # جعل اسم صاحب الحساب هو العنوان الأساسي أو يدمج معه ليكون مميزاً
        final_title = f"{uploader_name}"
    else:
        final_title = video_title

    # تنظيف العنوان من الرموز الممنوعة في أسماء الملفات
    final_title = re.sub(r'[\\/*?:"<>|]', "", final_title).strip()
    if not final_title:
        final_title = "Video"

    return {
        "title": final_title,
        "thumbnail": thumbnail,
        "combined_url": combined_url or (formats[0]["url"] if formats else ""),
        "video_url": video_url or combined_url or (formats[0]["url"] if formats else ""),
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

    raise Exception("No quality options available.")
