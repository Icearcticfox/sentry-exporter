from flask import Flask, Response

app = Flask(__name__)


@app.route("/health")
def health():
    return Response("OK", status=200, mimetype="text/plain")
