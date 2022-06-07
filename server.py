from flask import Flask
from flask import g

from flask_cors import CORS

from org_time import load_files, get_json_time

app = Flask(__name__)
CORS(app)


@app.route("/data")
def get_data():
    files = [
        "/home/valsdav/org/Clustering.org",
        "/home/valsdav/org/ETH.org",
        "/home/valsdav/org/CMS.org",
        "/home/valsdav/org/ttHbb.org",
        "/home/valsdav/org/Mails.org",
        "/home/valsdav/org/Publications.org"
    ]
    clock_root = load_files(files)
    return get_json_time(clock_root)
