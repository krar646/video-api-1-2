from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

# 1. تعريف تطبيق الفلاسك في البداية تماماً (هذا ما كان يسبب الخطأ)
app = Flask(__name__)
CORS(app)

# 2. إعدادات yt_dlp المتقدمة لتجنب الحظر
YDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "geo_bypass": True,
    "nocheckcertificate": True,
    "skip_download": True,
    "ignoreerrors": False,
    "extract_flat": False,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Sec-Fetch-Mode": "navigate"
    }
}

# 3. مسار فحص الحالة الرئيسي
@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "URL missing"}), 400

    url = data["url"]
    print("Extracting:", url)

    try:
        # إعدادات خاصة تجبر yt_dlp على اختيار صيغة MP4 واضحة ومدمجة لتجنب التلف
        ydl_opts_custom = YDL_OPTIONS.copy()
        ydl_opts_custom["format"] = "best[ext=mp4]/best"

        with yt_dlp.YoutubeDL(ydl_opts_custom) as ydl:
            info = ydl.extract_info(url, download=False)

        # إذا كان الفيديو يحتوي على رابط مباشرة أو formats
        formats = []
        fallback_url = info.get("url")

        for f in info.get("formats", []):
            f_url = f.get("url")
            if not f_url:
                continue

            # نأخذ فقط الصيغ التي تدعم MP4 وتجنب الصيغ الغريبة التي تسبب التشويش
            ext = f.get("ext")
            if ext != "mp4" and ext != "webm":
                continue

            has_video = f.get("vcodec") != "none" and f.get("vcodec") is not None
            has_audio = f.get("acodec") != "none" and f.get("acodec") is not None
            height = f.get("height") or 0

            formats.append({
                "format_id": f.get("format_id"),
                "url": f_url,
                "ext": ext,
                "height": height,
                "quality": f"{height}p" if height > 0 else "audio",
                "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                "has_video": has_video,
                "has_audio": has_audio
            })

        # إذا لم تجد القائمة صيغاً، نضع الرابط الأساسي كخطة بديلة آمنة
        if not formats and fallback_url:
            formats.append({
                "format_id": "default",
                "url": fallback_url,
                "ext": "mp4",
                "height": 720,
                "quality": "720p",
                "filesize": 0,
                "has_video": True,
                "has_audio": True
            })

        # اختيار أفضل رابط مدمج (فيديو وصوت معاً وبصيغة صحيحة)
        best_url = fallback_url
        for f in formats:
            if f.get("has_video") and f.get("has_audio"):
                best_url = f["url"]
                break

        return jsonify({
            "status": "success",
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "combined_url": best_url,
            "video_url": best_url,
            "audio_url": best_url,
            "formats": formats
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
