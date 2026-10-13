import yt_dlp
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

def extract_video_info(url):
    selected_user_agent = random.choice(USER_AGENTS)
    ydl_options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "skip_download": True,
        "ignoreerrors": True,
        "http_headers": {
            "User-Agent": selected_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise Exception("Failed to extract video info.")

    video_url = None
    audio_url = None
    combined_url = None
    formats_list = []

    for f in info.get("formats", []):
        f_url = f.get("url")
        if not f_url:
            continue

        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        height = f.get("height", 720)
        filesize = f.get("filesize")
        filesize_approx = f.get("filesize_approx")

        has_video = vcodec != "none" and vcodec is not None
        has_audio = acodec != "none" and acodec is not None

        if has_video and has_audio:
            combined_url = f_url
        elif has_video and not has_audio:
            video_url = f_url
        elif not has_video and has_audio:
            audio_url = f_url

        formats_list.append({
            "url": f_url,
            "quality": f"{height}p" if height else "720p",
            "has_video": has_video,
            "has_audio": has_audio,
            "filesize": filesize,
            "filesize_approx": filesize_approx
        })

    if not video_url:
        video_url = info.get("url")

    return {
        "title": info.get("title") or info.get("description") or "Video",
        "thumbnail": info.get("thumbnail", ""),
        "combined_url": combined_url,
        "video_url": video_url,
        "audio_url": audio_url,
        "formats": formats_list
    }