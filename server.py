from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

# 1. تعريف تطبيق الفلاسك
app = Flask(__name__)
CORS(app)

# 2. إعدادات yt_dlp المتقدمة لتجاوز القيود
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

# 4. مسار استخراج الروابط مع ضمان جلب الصوت والصورة معاً
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
        combined_url = None

        # فحص الصيغ المتاحة واستخراج الروابط بدقة
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
                "ext": f.get("ext", "mp4"),
                "height": height,
                "quality": f"{height}p" if height > 0 else "audio",
                "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                "has_video": has_video,
                "has_audio": has_audio
            }
            formats.append(item)

            # البحث الدقيق عن أول صيغة تحتوي على فيديو وصوت معاً لضمان عدم اكتمال التحميل بصوت فقط
            if has_video and has_audio and not combined_url:
                combined_url = f_url

        # إذا لم يتم العثور على رابط مدمج، نلجأ للرابط الأساسي كخطة بديلة
        if not combined_url:
            combined_url = info.get("url")

        return jsonify({
            "status": "success",
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "combined_url": combined_url,
            "formats": formats
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# 5. تشغيل السيرفر
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
