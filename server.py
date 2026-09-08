from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import random

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

@app.route("/")
def home():
    return jsonify({"status": "online", "message": "VidSnap API Secure & Running"})

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "URL missing"}), 400

    url = data["url"]
    print("Extracting for:", url)

    selected_user_agent = random.choice(USER_AGENTS)

    ydl_options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "skip_download": True,
        "ignoreerrors": True,
        "extractor_args": {
            "instagram": {
                "webpage_download": [True]
            }
        },
        "http_headers": {
            "User-Agent": selected_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Fetch-Mode": "navigate"
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"status": "error", "message": "Failed to extract video info or link restricted."}), 400

        formats = []
        best_url = None
        max_height = -1

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

            # اختيار الرابط الذي يحتوي على فيديو وصوت مدمجين معاً مسبقاً بأعلى جودة
            if has_video and has_audio:
                if height >= max_height:
                    max_height = height
                    best_url = f_url

        if not best_url:
            best_url = info.get("url")

        return jsonify({
            "status": "success",
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "combined_url": best_url,
            "formats": formats
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"status": "error", "message": "Server error while processing request."}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
