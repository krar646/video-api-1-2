from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import re
import os
import uuid
import tempfile
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================
# ✅ الإعدادات الأساسية
# ============================================================
DOWNLOAD_FOLDER = tempfile.gettempdir()

# ✅ قائمة المواقع المدعومة
SUPPORTED_SITES = [
    'facebook.com', 'fb.watch',
    'instagram.com', 'instagr.am',
    'tiktok.com', 'vm.tiktok.com',
    'twitter.com', 'x.com',
    'vimeo.com',
    'dailymotion.com',
    'twitch.tv',
    'reddit.com',
    'pinterest.com',
    'tumblr.com',
    'snapchat.com',
    'telegram.org',
    'whatsapp.com',
    'linkedin.com',
    'vine.co',
    'periscope.tv',
    'mixer.com',
    'vidme.com',
    'v Live.tv'
]

# ✅ إعدادات yt-dlp القوية
YDL_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'ignoreerrors': True,
    'extract_flat': False,
    'no_color': True,
    'geo_bypass': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'referer': 'https://www.google.com/',
    'force_generic_extractor': True,
    'cookiefile': None,
    'format_sort': ['res', 'codec'],
}

# ============================================================
# ✅ دالة التحقق من صحة الرابط
# ============================================================
def is_valid_url(url):
    url_lower = url.lower()

    # ❌ رفض يوتيوب نهائياً
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return False, "YouTube not supported"

    # ✅ قبول المواقع الأخرى
    for site in SUPPORTED_SITES:
        if site in url_lower:
            return True, None

    if url_lower.startswith('http'):
        return True, None

    return False, "Invalid URL"

# ============================================================
# ✅ دالة استخراج معلومات الفيديو
# ============================================================
def get_video_info(url):
    ydl_opts = YDL_OPTS_BASE.copy()
    ydl_opts['extract_flat'] = False

    if 'instagram.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
    elif 'tiktok.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (Linux; Android 11) Mobile'
    elif 'facebook.com' in url:
        ydl_opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

# ============================================================
# ✅ استخراج التنسيقات
# ============================================================
def extract_formats(info):
    formats = []

    for f in info.get('formats', []):
        if not f.get('url'):
            continue

        has_video = f.get('vcodec') != 'none'
        has_audio = f.get('acodec') != 'none'

        height = f.get('height', 0)
        quality = f"{height}p" if height > 0 else (f.get('format_note', 'Unknown'))

        formats.append({
            'format_id': f.get('format_id', 'unknown'),
            'quality': quality,
            'height': height,
            'ext': f.get('ext', 'mp4'),
            'url': f.get('url'),
            'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
            'filesize_mb': round((f.get('filesize') or 0) / (1024 * 1024), 2),
            'has_video': has_video,
            'has_audio': has_audio
        })

    formats.sort(key=lambda x: x['height'], reverse=True)
    return formats

def get_best_format(formats):
    video_with_audio = [f for f in formats if f['has_video'] and f['has_audio']]
    if video_with_audio:
        return video_with_audio[0]

    video_only = [f for f in formats if f['has_video']]
    if video_only:
        return video_only[0]

    return formats[0] if formats else None

# ============================================================
# ✅ API Routes
# ============================================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'success',
        'name': 'VidSnap Pro API',
        'version': '2.0.0',
        'message': 'API is running smoothly',
        'supported_sites': SUPPORTED_SITES
    })

@app.route('/extract', methods=['POST'])
def extract():
    try:
        data = request.get_json(silent=True)

        if not data or 'url' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No URL provided'
            }), 400

        url = data['url'].strip()

        is_valid, error_msg = is_valid_url(url)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_msg or 'URL not supported',
                'supported_sites': SUPPORTED_SITES
            }), 400

        info = get_video_info(url)
        formats = extract_formats(info)

        if not formats:
            return jsonify({
                'status': 'error',
                'message': 'No video formats found'
            }), 404

        best_format = get_best_format(formats)

        return jsonify({
            'status': 'success',
            'title': info.get('title', 'Untitled'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'upload_date': info.get('upload_date', ''),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'best_url': best_format['url'] if best_format else '',
            'best_quality': best_format['quality'] if best_format else '',
            'formats': formats
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json(silent=True)

        if not data or 'url' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No URL provided'
            }), 400

        url = data['url'].strip()
        format_id = data.get('format_id', 'best')

        is_valid, error_msg = is_valid_url(url)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_msg or 'URL not supported'
            }), 400

        unique_id = uuid.uuid4().hex
        output_path = os.path.join(DOWNLOAD_FOLDER, f"video_{unique_id}.mp4")

        ydl_opts = YDL_OPTS_BASE.copy()
        ydl_opts['outtmpl'] = output_path.replace('.mp4', '.%(ext)s')

        if format_id != 'best':
            ydl_opts['format'] = format_id
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        actual_file = None
        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(f"video_{unique_id}"):
                actual_file = os.path.join(DOWNLOAD_FOLDER, file)
                break

        if not actual_file or not os.path.exists(actual_file):
            return jsonify({
                'status': 'error',
                'message': 'Download failed'
            }), 500

        return send_file(
            actual_file,
            as_attachment=True,
            download_name=f"video_{unique_id}.mp4",
            mimetype='video/mp4'
        )

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/check', methods=['POST'])
def check_url():
    try:
        data = request.get_json(silent=True)
        url = data.get('url', '') if data else ''

        is_valid, error_msg = is_valid_url(url)

        site_name = 'Unknown'
        for site in SUPPORTED_SITES:
            if site in url.lower():
                site_name = site.split('.')[0].capitalize()
                break

        return jsonify({
            'status': 'success',
            'supported': is_valid,
            'message': error_msg if error_msg else ('Supported' if is_valid else 'Not supported'),
            'site': site_name,
            'url': url
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================
# ✅ تشغيل السيرفر
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
    ╔════════════════════════════════════════╗
    ║     VidSnap Pro API v2.0              ║
    ║     Server is running!                ║
    ║     Port: {port}                       ║
    ╚════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False)
