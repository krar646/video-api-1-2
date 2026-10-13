from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import urllib.parse
import re

# استيراد وحدات الاستخراج المستقلة
from extractors.video_extractor import extract_video_info
from extractors.image_extractor import extract_image_info
from extractors.pdf_extractor import extract_pdf_info

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"status": "online", "message": "Multi-Tool Downloader API is Running perfectly!"})

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "URL missing"}), 400

    url = data["url"]
    media_type = data.get("type", "video") # تحديد نوع الطلب (video, image, pdf) قادم من الفلاتر

    # تنظيف روابط الـ intent إن وجدت
    if url.startswith("intent://"):
        try:
            if "browser_fallback_url=" in url:
                parts = url.split("browser_fallback_url=")
                fallback = parts[1].split(";")[0]
                url = urllib.parse.unquote(fallback)
            else:
                match = re.search(r'(https?://[^\s]+)', url)
                if match:
                    url = match.group(1)
        except Exception as e:
            print("Intent parsing error:", e)

    try:
        result = {}
        if media_type == "video":
            result = extract_video_info(url)
        elif media_type == "image":
            result = extract_image_info(url)
        elif media_type == "pdf" or media_type == "document":
            result = extract_pdf_info(url)
        else:
            # افتراضياً إذا لم يتم تحديد النوع، نجرب الفيديو عبر yt-dlp
            result = extract_video_info(url)

        return jsonify({
            "status": "success",
            "type": media_type,
            **result
        })

    except Exception as e:
        print("EXTRACTION ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
