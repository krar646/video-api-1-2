import yt_dlp
import random
import os
import requests
from bs4 import BeautifulSoup
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

def extract_video_info(url):
    selected_user_agent = random.choice(USER_AGENTS)
    cookies_path = os.path.join(os.path.dirname(__file__), '..', 'cookies.txt')

    # -------------------------------------------------------------
    # الطريقة الأولى: yt-dlp مع ملف الكوكيز
    # -------------------------------------------------------------
    try:
        ydl_options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "skip_download": True,
            "ignoreerrors": True,
            "cookiefile": cookies_path,
            "http_headers": {"User-Agent": selected_user_agent}
        }
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and (info.get('url') or info.get('formats')):
            return format_ytdlp_result(info)
    except Exception as e:
        print(f"Fallback 1 (yt-dlp with cookies) failed: {str(e)}")

    # -------------------------------------------------------------
    # الطريقة الثانية: yt-dlp بدون ملف الكوكيز
    # -------------------------------------------------------------
    try:
        ydl_options_no_cookies = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "skip_download": True,
            "ignoreerrors": True,
            "http_headers": {"User-Agent": selected_user_agent}
        }
        with yt_dlp.YoutubeDL(ydl_options_no_cookies) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and (info.get('url') or info.get('formats')):
            return format_ytdlp_result(info)
    except Exception as e:
        print(f"Fallback 2 (yt-dlp without cookies) failed: {str(e)}")

    # -------------------------------------------------------------
    # الطريقة الثالثة: استخدام مكتبة Streamlink لاستخراج الروابط
    # -------------------------------------------------------------
    try:
        import streamlink
        streams = streamlink.streams(url)
        if streams:
            best_stream = streams.get("best") or list(streams.values())[0]
            stream_url = best_stream.url
            return {
                "title": "Video Stream",
                "thumbnail": "",
                "combined_url": stream_url,
                "video_url": stream_url,
                "audio_url": None,
                "formats": [{"url": stream_url, "quality": "HD", "has_video": True, "has_audio": True}]
            }
    except Exception as e:
        print(f"Fallback 3 (Streamlink) failed: {str(e)}")

    # -------------------------------------------------------------
    # الطريقة الرابعة: السحب المباشر عبر BeautifulSoup و Regex
    # -------------------------------------------------------------
    try:
        headers = {"User-Agent": selected_user_agent, "Referer": url}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        video_urls = []
        for v in soup.find_all(['video', 'source']):
            src = v.get('src')
            if src and src.startswith('http'):
                video_urls.append(src)
        
        mp4_matches = re.findall(r'https?://[^\s<>"]+?\.(?:mp4|m3u8|webm)', response.text)
        for m in mp4_matches:
            if m not in video_urls:
                video_urls.append(m)

        if video_urls:
            direct_url = video_urls[0]
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else "Video"
            return {
                "title": title,
                "thumbnail": "",
                "combined_url": direct_url,
                "video_url": direct_url,
                "audio_url": None,
                "formats": [{"url": direct_url, "quality": "HD", "has_video": True, "has_audio": True}]
            }
    except Exception as e:
        print(f"Fallback 4 (Scraper) failed: {str(e)}")

    # إذا فشلت جميع الطرق الأربع معاً
    raise Exception("No quality options available.")

def format_ytdlp_result(info):
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
        })

    if not video_url:
        video_url = info.get("url")

    return {
        "title": info.get("title") or "Video",
        "thumbnail": info.get("thumbnail", ""),
        "combined_url": combined_url,
        "video_url": video_url,
        "audio_url": audio_url,
        "formats": formats_list
    }
