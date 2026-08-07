from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)


YDL_OPTIONS = {

    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,

    "geo_bypass": True,
    "nocheckcertificate": True,

    "http_headers": {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    },

    # استخراج فقط بدون تحميل
    "skip_download": True,

    "ignoreerrors": False,
}



@app.route("/")
def home():

    return jsonify({
        "status": "online",
        "message": "VidSnap API Running"
    })




@app.route("/extract", methods=["POST"])
def extract():

    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({
            "error": "URL missing"
        }),400


    url = data["url"]

    print("Extracting:", url)


    try:

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )



        formats = []


        for f in info.get("formats", []):


            if not f.get("url"):
                continue


            has_video = (
                f.get("vcodec")
                and f.get("vcodec") != "none"
            )


            has_audio = (
                f.get("acodec")
                and f.get("acodec") != "none"
            )


            height = f.get("height") or 0



            if height > 0:
                quality = f"{height}p"
            else:
                quality = "Audio"



            formats.append({

                "format_id":
                f.get("format_id"),


                "quality":
                quality,


                "height":
                height,


                "ext":
                f.get("ext"),


                "url":
                f.get("url"),


                "filesize":
                f.get("filesize")
                or f.get("filesize_approx")
                or 0,


                "has_video":
                bool(has_video),


                "has_audio":
                bool(has_audio),


                "headers":
                f.get("http_headers", {})

            })




        # حذف التكرار
        unique_formats = []

        seen = set()


        for f in formats:

            key = (
                f["quality"],
                f["ext"],
                f["has_video"],
                f["has_audio"]
            )

            if key not in seen:

                seen.add(key)
                unique_formats.append(f)



        unique_formats.sort(
            key=lambda x:x["height"],
            reverse=True
        )



        return jsonify({

            "status":
            "success",


            "title":
            info.get("title","Video"),


            "thumbnail":
            info.get("thumbnail",""),


            "duration":
            info.get("duration",0),


            "formats":
            unique_formats

        })



    except Exception as e:


        print("ERROR:",e)


        return jsonify({

            "status":
            "error",

            "message":
            str(e)

        }),500






if __name__=="__main__":


    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port
    )
