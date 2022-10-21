from flask import Flask, request
from flask import g
import time
from flask_cors import CORS
from datetime import datetime

from org_time import load_files, get_json_time

app = Flask(__name__)
CORS(app)


@app.route("/data")
def get_data():
    args = request.args
    start_time = args.get("start", None)
    end_time = args.get("end", None)
    if start_time:
        start_time = datetime.fromisoformat(start_time)
    if end_time:
        end_time = datetime.fromisoformat(end_time)
    files = [
        "/home/valsdav/org/Clustering.org",
        "/home/valsdav/org/ETH.org",
        "/home/valsdav/org/CMS.org",
        "/home/valsdav/org/ttHbb.org",
        "/home/valsdav/org/Mails.org",
        "/home/valsdav/org/Publications.org",
        "/home/valsdav/org/Meetings.org",
        "/home/valsdav/org/L3_ML_production.org",
        "/home/valsdav/org/Reading.org",
        "/home/valsdav/org/Learning.org"
    ]
    clock_root = load_files(files, start_time, end_time)
    return get_json_time(clock_root)
