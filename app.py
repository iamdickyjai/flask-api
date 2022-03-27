# from diarization import diar
from typing import final
from flask import Flask
from flask import jsonify, make_response, send_file
from flask import request
from flask_cors import CORS, cross_origin
import tempfile
import os
import glob
from youtube_dl.postprocessor import ffmpeg
from youtube_dl.utils import DownloadError
import diarization as diar
import logging
import youtube_dl
import sox
from pydub import AudioSegment

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

class UnidentifiedException(Exception):
    pass

@app.route("/", methods=["POST"])
@cross_origin(origins=["*"])
def main():
    data = request.files["file"]
    byte = data.read()
    
    if not os.path.isdir("temp"):
        os.mkdir("temp")

    try:
        path = convert2WAV(data, byte)
        result = diar.diarization(path)

        response = jsonify({"result": result})

        return response
    except Exception as e:
        print(e)

        if type(e) is UnidentifiedException:
            return make_response(jsonify({"Error": "File format unidentified!"}), 400)

        return make_response(jsonify({"Error": "Error happened"}), 500)
    finally:
        os.system('rm -rf temp')

# Download mp3 file to client
@app.route("/download", methods=["POST"])
@cross_origin(origins=["*"])
def dl():
    content = request.json
    
    if "url" in content:
        # shell = os.path.join(os.getcwd(), "wget_youtube.sh")
        url = content['url']
        tmp = tempfile.TemporaryDirectory()
        path = "{}/download.mp3".format(tmp.name)
        try:
            ydl_opts = {
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': path
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
                
            return send_file(path)
        finally:
            tmp.cleanup()

    else:
        logging.error("URL not found")
        return make_response(jsonify("URL not found"), 400)

def convert2WAV(data, byte):
    content_type = data.content_type

    print('Start converting...')

    if 'wav' in content_type:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')  
        tmp.write(byte)   

    elif 'mpeg' in content_type:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')  
        tmp.write(byte)   

    elif 'flac' in content_type:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.flac')
        tmp.write(byte)

    elif 'm4a' in content_type:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.m4a')
        tmp.write(byte)

    else:
        print(content_type)
        raise UnidentifiedException
        
    audio = AudioSegment.from_file(tmp.name)
    audio.export('temp/audio.wav', format='wav')

    tmp.close()
    os.unlink(tmp.name)

    os.system("ffmpeg -i {} -ar 16000 -acodec pcm_s16le -ac 1 {}".format("temp/audio.wav", "temp/result.wav"))

    return "temp/result.wav"
