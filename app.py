from flask import Flask
import os

app = Flask(__name__)


@app.get("/")
def index():
    return {
        "message": "hello from Kubernetes.",
        "version": os.getenv("APP_VERSION", "local"),
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
