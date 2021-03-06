#!/usr/bin/python
# coding=utf-8
"""
Author: tal 
Created on 05/05/2018

"""
import base64
import os

from backend import predictor
from flask import Flask, jsonify, request, render_template

from backend.cors import crossdomain
from seq2seq.util.checkpoint import Checkpoint

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'access.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },

    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s',
        },
        'email': {
            'format': 'Timestamp: %(asctime)s\nModule: %(module)s\n Line: %(lineno)d\nMessage: %(message)s',
        },
    },
    'loggers': {
        'extensive': {
            'level': 'DEBUG',
            'handlers': ['file']
        },
    }
})

app = Flask(__name__)
app.config.from_object(__name__)  # load config from this file , flaskr.py

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD=os.environ.get("DEV_PASS", "SECRET"),
    EXPERIMENT_PATH=os.environ.get("EXPERIMENT_PATH")
))

BASE_CHECKPOINT_DIR = os.path.join(app.config.get('EXPERIMENT_PATH'), Checkpoint.CHECKPOINT_DIR_NAME)


def get_dates():
    checkpoints_dir = os.path.join(app.config.get('EXPERIMENT_PATH'), Checkpoint.CHECKPOINT_DIR_NAME)
    print(checkpoints_dir)
    return os.listdir(checkpoints_dir)


def get_epochs_list(dates_dir):
    return os.listdir(os.path.join(BASE_CHECKPOINT_DIR, dates_dir))


def get_checkpoints(dates_dir, epoch_dir):
    return os.listdir(os.path.join(BASE_CHECKPOINT_DIR, dates_dir, epoch_dir))


def get_args(req):
    if req.method == 'POST':
        args = req.json
    elif req.method == "GET":
        args = req.args
    return args


@app.route("/_get_epochs", methods=["GET", "POST", "OPTIONS"])
@crossdomain(origin='*', headers="Content-Type")
def get_epochs():
    args = get_args(request)
    return jsonify(epoches=sorted(get_epochs_list(args.get('date')), key=int))


@app.route("/_get_steps", methods=["GET", "POST", "OPTIONS"])
@crossdomain(origin='*', headers="Content-Type")
def get_steps():
    args = get_args(request)
    return jsonify(steps=sorted(get_checkpoints(args.get('date'), args.get('epoch'))))


@app.route("/_get_dates", methods=["GET", "POST", "OPTIONS"])
@crossdomain(origin='*', headers="Content-Type")
def _get_dates():
    return jsonify(dates=sorted(get_dates()))


@app.route("/_predict", methods=["GET", "POST", "OPTIONS"])
@crossdomain(origin='*', headers="Content-Type")
def predict():
    args = get_args(request)
    seq_str = None
    if args is not None:
        seq_str = args.get('seq_str')
    if seq_str is not None:
        try:
            seq_str = base64.b64decode(seq_str)
        except Exception as e:
            app.logger.error(str(e))
            return jsonify({"error": "Bad Request",
                            "error_description": "expected Base64 encoded data"}), 400
        date = args.get('date', "2018_05_24")
        epoch = args.get('epoch', "300")
        step = args.get('step', "2018_05_24_23_11_33_S5400")
        try:
            suggestions = predictor.predict(expt_dir=app.config.get('EXPERIMENT_PATH'),
                                            date=date,
                                            epoch=epoch,
                                            step=step,
                                            seq_str=seq_str, n=3)
            return jsonify({"data": {"results": [' '.join(x).strip() for x in suggestions]}}), 200
        except Exception:
            return jsonify({"error": "Bad Request", "error_description": "expected Base64 encoded data"}), 400
    else:
        return jsonify({"error": "Bad Request"}), 400


@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@app.route("/", methods=["GET"])
def index():
    models = sorted(get_dates())
    return render_template('index.html', models=models)


def main(host="0.0.0.0", port=5000):
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
