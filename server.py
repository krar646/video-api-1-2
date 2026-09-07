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
@app.route("/")
def home():
    return jsonify({"status": "online", "message": "VidSnap API Running"})

# 4. مسار استخراج الروابط والفيديو (بالحماية الكاملة لمنع القيم الفارغة)
@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "URL missing"}), 400

    url = data["url"]
    print("Extracting:", url)

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        combined_formats = []
        video_formats = []
        audio_formats = []

        # استخراج الصيغ المتاحة
        for f in info.get("formats", []):
            f_url = f.get("url")
            if not f_url:
                continue

            has_video = f.get("vcodec") != "none" and f.get("vcodec") is not None
            has_audio = f.get("acodec") != "none" and f.get("acodec") is not None
            height = f.get("height") or 0

            item = {
                "format_id": f.get("format_id"),
                "url": f_url,
                "ext": f.get("ext"),
                "height": height,
                "quality": f"{height}p" if height > 0 else "audio",
                "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                "has_video": has_video,
                "has_audio": has_audio
            }

            formats.append(item)

            if has_video and has_audio:
                combined_formats.append(item)
            elif has_video:
                video_formats.append(item)
            elif has_audio:
                audio_formats.append(item)

        combined_formats.sort(key=lambda x: x["height"], reverse=True)
        video_formats.sort(key=lambda x: x["height"], reverse=True)
        audio_formats.sort(key=lambda x: x.get("filesize", 0), reverse=True)

        # 🛡️ الخطة البديلة لمنع رجوع الروابط فارغة نهائياً:
        fallback_url = info.get("url")

        # تحديد رابط الـ combined
        final_combined = None
        if combined_formats:
            final_combined = combined_formats[0]["url"]
        elif video_formats:
            final_combined = video_formats[0]["url"]
        else:
            final_combined = fallback_url

        # تحديد رابط الفيديو فقط
        final_video = None
        if video_formats:
            final_video = video_formats[0]["url"]
        else:
            final_video = fallback_url

        # تحديد رابط الصوت فقط
        final_audio = None
        if audio_formats:
            final_audio = audio_formats[0]["url"]

        # إذا كانت القائمة formats فارغة تماماً، ننشئ عنصراً افتراضياً
        if not formats and fallback_url:
            formats.append({
                "format_id": "default",
                "url": fallback_url,
                "ext": info.get("ext", "mp4"),
                "height": 720,
                "quality": "720p",
                "filesize": 0,
                "has_video": True,
                "has_audio": True
            })

        return jsonify({
            "status": "success",
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "combined_url": final_combined,
            "video_url": final_video,
            "audio_url": final_audio,
            "formats": formats
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# 5. تشغيل السيرفر في النهاية
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
