from flask import Flask, request
from policyengine import Simulation
import os
from supabase import create_client, Client
from threading import Thread
import datetime
import traceback
import plotly.graph_objects as go

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = Flask(__name__)

def safe_json_decode(data):
    # Decode JSON data, cast all float-like values to python float (e.g. no float32)

    def _safe_json_decode(data):
        if isinstance(data, dict):
            return {key: _safe_json_decode(value) for key, value in data.items()}
        if isinstance(data, go.Figure):
            return data.to_json()
        if isinstance(data, list):
            return [_safe_json_decode(item) for item in data]
        if not isinstance(data, str):
            try:
                return float(data)
            except ValueError:
                return data
        return data
    
    return _safe_json_decode(data)

def run_compute(job_id):
    print(f"Running job {job_id}")
    # Supabase. Get job with job id and print options

    job = supabase.table("job").select("*").eq("id", job_id).execute()
    
    if len(job.data) == 0:
        return

    job = job.data[0]

    # Set job status to running

    supabase.table("job").update({
        "status": "running",
        "started_at": datetime.datetime.now().isoformat(),
    }).eq("id", job_id).execute()

    try:
        options = job["options"]
        path = options.pop("path")
        kwargs = options.pop("kwargs", {})
        simulation = Simulation(
            **options,
        )
        print(path)
        result = simulation.calculate(path or "/", **kwargs)
        result = safe_json_decode(result)

        # Set job status to complete and fill result

        supabase.table("job").update({
            "status": "complete",
            "result": result
        }).eq("id", job_id).execute()
    
    except Exception as e:
        # Set job status to error and fill error

        supabase.table("job").update({
            "status": "error",
            "result": {"error": traceback.format_exc()}
        }).eq("id", job_id).execute()

    print(f"Completed job {job_id}")

@app.route("/compute", methods=["GET"])
def compute():
    job_id = request.args.get("job_id")
    if job_id is not None:
        Thread(target=run_compute, args=(job_id,)).start()
    else:
        jobs = supabase.table("job").select("*").eq("status", "queued").execute().data
        if len(jobs) > 0:
            job_id = jobs[0]["id"]
            Thread(target=run_compute, args=(job_id,)).start()
    
    return {
        "status": "ok",
        "job_started": job_id,
    }

@app.route("/", methods=["GET"])
def index():
    return {
        "status": "ok"
    }
