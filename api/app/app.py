from flask import Flask, request
from policyengine import Simulation
import os
from supabase import create_client, Client
from threading import Thread
from dotenv import load_dotenv
import json
import requests

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return {
        "status": "ok"
    }

@app.route("/compute", methods=["POST"])
def compute():
    options = request.json

    # Add new job to jobs table, status = queued, options=options and get job id
    job = supabase.table("job").insert({
        "status": "queued",
        "options": options,
    }).execute()

    # Find all queued jobs and run them

    jobs = supabase.table("job").select("*").eq("status", "queued").execute()

    for job in jobs.data:
        job_id = job["id"]
        requests.post(f"https://policyengine-server-70913873059.us-central1.run.app/compute?job_id={job_id}")

    return {
        "status": "ok"
    }

if __name__ == "__main__":
    app.run(port=os.environ.get("PORT", 8080), host="0.0.0.0")