from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__)
CORS(app)

# ✅ إعدادات متقدمة
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'ignoreerrors': True,
    'extract_flat': 'in_playlist',
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []

            # ✅ الطريقة الأولى: جلب التنسيقات
            for f in info.get('formats', []):
                if not f.get('url'):
                    continue

                formats.append({
                    'quality': f"{f.get('height', 0)}p" if f.get('height', 0) > 0 else 'Audio',
                    'height': f.get('height', 0) or 0,
                    'ext': f.get('ext', 'mp4'),
                    'url': f.get('url'),
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                    'has_video': f.get('vcodec') != 'none',
                    'has_audio': f.get('acodec') != 'none',
                    'format_id': f.get('format_id', 'unknown')
                })

            # ✅ الطريقة الثانية: جلب الرابط المباشر من `url` أو `manifest_url`
            if not formats:
                direct_url = info.get('url') or info.get('manifest_url')
                if direct_url:
                    formats.append({
                        'quality': 'Best',
                        'height': 0,
                        'ext': 'mp4',
                        'url': direct_url,
                        'filesize': 0,
                        'has_video': True,
                        'has_audio': True,
                        'format_id': 'best'
                    })

            # ✅ الطريقة الثالثة: جلب من `requested_formats`
            if not formats and info.get('requested_formats'):
                for f in info['requested_formats']:
                    if f.get('url'):
                        formats.append({
                            'quality': f.get('format_note', 'Best'),
                            'height': 0,
                            'ext': f.get('ext', 'mp4'),
                            'url': f.get('url'),
                            'filesize': 0,
                            'has_video': True,
                            'has_audio': True,
                            'format_id': f.get('format_id', 'best')
                        })

            # ✅ ترتيب حسب الجودة
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
