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





# اختبار السيرفر

@app.route("/")
def home():

    return jsonify({

        "status":"online",

        "message":"VidSnap API Running"

    })






# استخراج الفيديو

@app.route("/extract", methods=["POST"])
def extract():


    data = request.get_json()



    if not data or "url" not in data:


        return jsonify({

            "status":"error",

            "message":"URL missing"

        }),400




    url = data["url"]


    print("Extracting:",url)



    try:



        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:


            info = ydl.extract_info(

                url,

                download=False

            )






        formats = []



        combined_formats = []

        video_formats = []

        audio_formats = []






        for f in info.get("formats", []):



            if not f.get("url"):

                continue






            has_video = (

                f.get("vcodec") != "none"

                and

                f.get("vcodec") is not None

            )




            has_audio = (

                f.get("acodec") != "none"

                and

                f.get("acodec") is not None

            )





            height = f.get("height") or 0






            item = {


                "format_id":

                f.get("format_id"),



                "url":

                f.get("url"),



                "ext":

                f.get("ext"),




                "height":

                height,



                "quality":

                f"{height}p"

                if height > 0

                else "audio",




                "filesize":

                f.get("filesize")

                or

                f.get("filesize_approx")

                or 0,




                "has_video":

                has_video,




                "has_audio":

                has_audio

            }







            formats.append(item)







            # فيديو + صوت جاهز

            if has_video and has_audio:


                combined_formats.append(item)






            # فيديو فقط

            elif has_video:


                video_formats.append(item)







            # صوت فقط

            elif has_audio:


                audio_formats.append(item)









        # ترتيب الجودة


        combined_formats.sort(

            key=lambda x:x["height"],

            reverse=True

        )



        video_formats.sort(

            key=lambda x:x["height"],

            reverse=True

        )







        combined_url = None

        video_url = None

        audio_url = None






        if combined_formats:

            combined_url = combined_formats[0]["url"]






        if video_formats:

            video_url = video_formats[0]["url"]






        if audio_formats:

            audio_url = audio_formats[0]["url"]






        return jsonify({



            "status":"success",




            "title":

            info.get(

                "title",

                "Video"

            ),





            "thumbnail":

            info.get(

                "thumbnail",

                ""

            ),




            "duration":

            info.get(

                "duration",

                0

            ),




            # جاهز فيديو وصوت

            "combined_url":

            combined_url,





            # يحتاج دمج داخل الهاتف

            "video_url":

            video_url,





            "audio_url":

            audio_url,





            "formats":

            formats




        })







    except Exception as e:



        print("ERROR:",e)



        return jsonify({


            "status":"error",


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
