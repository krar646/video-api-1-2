from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import random
import urllib.parse
import re

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

@app.route("/")
def home():
    return jsonify({"status": "online", "message": "VidSnap Multi-Platform API is Running"})

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "URL missing"}), 400

    url = data["url"]

    # تنظيف روابط الـ intent لجميع المنصات وتحويلها إلى روابط http/https صالحة
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

    print("Extracting URL for all platforms:", url)
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
                "vcodec": vcodec,
                "acodec": acodec
            })

        if not video_url:
            video_url = info.get("url")

        return jsonify({
            "status": "success",
            "title": info.get("title") or info.get("description") or "Video",
            "thumbnail": info.get("thumbnail", ""),
            "combined_url": combined_url,
            "video_url": video_url,
            "audio_url": audio_url,
            "formats": formats_list
        })

    except Exception as e:
        print("EXTRACTION ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
