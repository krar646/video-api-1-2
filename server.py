from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

# ✅ إعدادات خاصة لإنستغرام والمواقع الصعبة
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'ignoreerrors': True,
    'extract_flat': False,
    'no_color': True,
    'geo_bypass': True,
    'cookiefile': None,
    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'referer': 'https://www.instagram.com/',
}

@app.route("/")
def home():
    return "VidSnap API Running"

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True)

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]
    print(f"📥 Extracting: {url}")

    ydl_opts = YDL_OPTS.copy()
    
    if 'instagram.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
        ydl_opts['extract_flat'] = False
        ydl_opts['cookiefile'] = None
    elif 'tiktok.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (Linux; Android 11) Mobile'
    elif 'facebook.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []

            for f in info.get('formats', []):
                if not f.get('url'):
                    continue

                has_video = f.get('vcodec') != 'none'
                has_audio = f.get('acodec') != 'none'

                if has_video or has_audio:
                    height = f.get('height', 0)
                    quality = f"{height}p" if height and height > 0 else 'Audio' if has_audio else 'Video'
                    
                    formats.append({
                        'quality': quality,
                        'height': height if height is not None else 0,
                        'ext': f.get('ext', 'mp4'),
                        'url': f.get('url'),
                        'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                        'has_video': has_video,
                        'has_audio': has_audio,
                        'format_id': f.get('format_id', 'unknown')
                    })

            # ✅ الترتيب الصحيح (تجنب None)
            formats.sort(key=lambda x: x['height'] if x['height'] is not None else 0, reverse=True)

            best_format = next((f for f in formats if f['has_video'] and f['has_audio']), formats[0] if formats else None)

            return jsonify({
                'status': 'success',
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'best_url': best_format['url'] if best_format else '',
                'formats': formats
            })

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
