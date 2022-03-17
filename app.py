# from diarization import diar
from flask import Flask
from flask import jsonify, make_response
from flask import request
from flask_cors import CORS, cross_origin
import tempfile
import os
import diarization as diar
import logging
import sys
import subprocess
import shlex

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
        tmp = tempfile.TemporaryDirectory()
        try:
            path = "{}/rec0087.wav".format(tmp.name)
            subprocess.call(shlex.split('{} "{}" {}'.format("./wget_youtube.sh", url, path)))

            result = diar.diarization(path)

            response = jsonify({"result": result})

            return response
        except Exception as e:
            return make_response(
                jsonify({"Error": str(e), "Path": os.listdir(".")}), 500
            )
        finally:
            tmp.cleanup()
    else:
        logging.error("URL not found")
        return make_response(jsonify("URL not found"), 400)
