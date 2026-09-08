from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import random

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
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

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"status": "error", "message": "Failed to extract info."}), 400

        video_url = None
        audio_url = None
        combined_url = None

        for f in info.get("formats", []):
            f_url = f.get("url")
            if not f_url:
                continue
            
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")

            # البحث عن رابط مدمج إن وجد
            if vcodec != "none" and vcodec is not None and acodec != "none" and acodec is not None:
                combined_url = f_url
            # البحث عن فيديو منفصل
            elif vcodec != "none" and vcodec is not None and (acodec == "none" or acodec is None):
                video_url = f_url
            # البحث عن صوت منفصل
            elif (vcodec == "none" or vcodec is None) and acodec != "none" and acodec is not None:
                audio_url = f_url

        # إذا لمن نجد منفصلين، نعتمد الرابط العام
        if not combined_url and not video_url:
            combined_url = info.get("url")

        return jsonify({
            "status": "success",
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "combined_url": combined_url,
            "video_url": video_url,
            "audio_url": audio_url,
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
