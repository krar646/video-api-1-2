import yt_dlp
import random
import os
import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

def extract_video_info(url):
    # المحاولة الأولى: باستخدام العملاق yt-dlp مع ملف الكوكيز
    try:
        selected_user_agent = random.choice(USER_AGENTS)
        cookies_path = os.path.join(os.path.dirname(__file__), '..', 'cookies.txt')

        ydl_options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "skip_download": True,
            "ignoreerrors": True,
            "cookiefile": cookies_path,
            "http_headers": {
                "User-Agent": selected_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        }

        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)

        if info:
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
    except Exception as e:
        print(f"yt-dlp failed, switching to fallback extractor: {str(e)}")

    # -------------------------------------------------------------
    # المحاولة الثانية (Fallback): السحب المباشر عبر BeautifulSoup 
    # (تنفع جداً مع المواقع التي تعرض فيديو بمشغل HTML5 مباشر)
    # -------------------------------------------------------------
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن وسوم الفيديو المباشرة أو روابط الـ mp4 في مصدر الصفحة
        video_tag = soup.find('video')
        direct_url = None
        
        if video_tag and video_tag.get('src'):
            direct_url = video_tag.get('src')
        else:
            # البحث عن أي رابط ينتهي بـ .mp4 داخل الصفحة
            source_tag = soup.find('source', type='video/mp4')
            if source_tag and source_tag.get('src'):
                direct_url = source_tag.get('src')

        if direct_url:
            return {
                "title": soup.title.string if soup.title else "Video",
                "thumbnail": "",
                "combined_url": direct_url,
                "video_url": direct_url,
                "audio_url": None,
                "formats": [{"url": direct_url, "quality": "HD", "has_video": True, "has_audio": True}]
            }
    except Exception as fallback_error:
        print(f"Fallback extractor also failed: {str(fallback_error)}")

    # إذا فشلت كل المحاولات
    raise Exception("No quality options available for this link.")
