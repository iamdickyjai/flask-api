# from diarization import diar
from typing import final
from flask import Flask
from flask import jsonify, make_response
from flask import request
from flask_cors import CORS, cross_origin
import tempfile
import os
import diarization as diar
import logging
import youtube_dl
import sox

# Logging setting
# root = logging.getLogger()
# root.setLevel(logging.DEBUG)

# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# root.addHandler(handler)

app = Flask(__name__)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

cors = CORS(app, resources={r"/*": {"origins": "*"}})
# app.config['CORS_HEADERS'] = 'Content-Type'


@app.route("/", methods=["POST"])
@cross_origin(origins=["*"])
def main():
    data = request.files["file"]
    byte = data.read()

    # Assume wav only
    # Setup the properties of the audio
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        # Create temporary directory for diarization
        tmp.write(byte)
        result = diar.diarization(tmp.name)

        response = jsonify({"result": result})

        return response
    except Exception:
        return make_response(jsonify({"Error": "Error happened"}), 500)
    finally:
        tmp.close()
        os.unlink(tmp.name)

@app.route("/youtube", methods=["POST"])
@cross_origin(origins=["*"])
def dl():
    content = request.json
    if "url" in content:
        # shell = os.path.join(os.getcwd(), "wget_youtube.sh")
        url = content['url']
        try:
            wget_youtube(url)

            result = diar.diarization("audio/result.wav")

            response = jsonify({"result": result})
            return response

        except Exception as e:
            return make_response(
                jsonify({"Error": str(e), "Path": os.listdir(".")}), 500
            )
        finally:
            if os.path.exists("audio/result.wav"):
                os.remove("audio/result.wav")
    else:
        logging.error("URL not found")
        return make_response(jsonify("URL not found"), 400)

# Download audio from YouTube url
def wget_youtube(url):
    # Create a temporary file for ffmpeg
    tmp = tempfile.TemporaryDirectory()
    path = "{}/rec0087.wav".format(tmp.name)

    if not os.path.isdir("audio"):
        os.mkdir("audio")

    try:
        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': path
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            length = info.get('duration')
               
            os.system("ffmpeg -i {} -ar 16000 -acodec pcm_s16le -af 'pan=mono|FC=FR' {}".format(path, "./audio/ffmpeg.wav"))

            # Python Soc documentation
            # https://github.com/rabitt/pysox/blob/master/sox/transform.py
            tfm = sox.Transformer()
            if length > 180:
                tfm.trim(90, length-90)
            tfm.silence(location=1, silence_threshold=1, min_silence_duration=0.1)
            tfm.silence(location=-1, silence_threshold=1, min_silence_duration=0.1)
            tfm.build("audio/ffmpeg.wav", "audio/result.wav")
    finally:
        if os.path.exists("audio/ffmpeg.wav"):
            os.remove("audio/ffmpeg.wav")
        tmp.cleanup()