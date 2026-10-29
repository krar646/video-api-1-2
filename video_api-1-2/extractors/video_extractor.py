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

    # ترتيب الـ formats بحيث نبحث عن أعلى جودة متوفرة أولاً (مثل 720p ثم 480p)
    raw_formats = info.get("formats", [])

    # محاولة إعطاء الأولوية للـ formats التي تحتوي على فيديو وصوت معاً أو جودات واضحة
    for f in raw_formats:
        url = f.get("url")
        if not url:
            continue

        height = f.get("height")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")

        has_video = vcodec not in (None, "none")
        has_audio = acodec not in (None, "none")

        if has_video and height:
            # تحديد الدقة بدقة وبدون فقدان جودة
            if height >= 720:
                q_str = "720p"
            elif height >= 480:
                q_str = "480p"
            else:
                q_str = f"{height}p"

            # نركز على 720p و 480p ونمنع التكرار مع إعطاء الأولوية لـ 720p الحقيقية
            if q_str not in seen_qualities and q_str in ["720p", "480p"]:
                seen_qualities.add(q_str)
                formats.append({
                    "url": url,
                    "quality": q_str,
                    "has_video": True,
                    "has_audio": has_audio,
                })

                # إذا وجدنا رابط يدمج الفيديو والصوت بدقة 720p نجعله الأساس فوراً
                if q_str == "720p" and has_audio and not combined_url:
                    combined_url = url
                elif not combined_url and has_audio:
                    combined_url = url

                if has_video and not video_url:
                    video_url = url

        # استخراج الصوت النقي المنفصل لخيار Fast Audio
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

    # إذا لم نجد روابط مدمجة واضحة، نبحث عن أفضل رابط فيديو منفصل أو متاح
    if not combined_url and formats:
        for fmt in formats:
            if fmt["quality"] == "720p" and fmt["url"]:
                combined_url = fmt["url"]
                break
        if not combined_url:
            combined_url = formats[0]["url"]

    # إذا لم يتم رصد جودات محددة، نأخذ رابط الفيديو الأساسي كحل احتياطي
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
