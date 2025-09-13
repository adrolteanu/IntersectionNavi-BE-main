import os
import datetime
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from dotenv import load_dotenv

from simulation_engine import run_simulations

# Performance Monitoring
from performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()

# Load environment and init Flask
load_dotenv()
app = Flask(__name__)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["traffic_db"]
vehicles_col = db["vehicles"]

def scheduled_run():
    """
    This job runs once per minute in the background,
    simulates all vehicles, and writes recommendedSpeed + lastSimulation.
    """
    monitor.mark_db_fetch_start()
    clients = list(vehicles_col.find({}, {"_id": 0}))
    monitor.mark_db_fetch_end(len(clients))

    if not clients:
        return

    monitor.mark_simulation_start("scheduled_run")
    sim = run_simulations(clients)
    monitor.mark_simulation_end()

    rec_speed = sim["recommendedSpeed"]
    ts = datetime.datetime.utcnow().isoformat() + "Z"

    vehicles_col.update_many(
        {}, 
        {"$set": {"recommendedSpeed": rec_speed,
                  "lastSimulation": ts}}
    )

    monitor.finalize("results")

# Start the background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_run, "interval", minutes=1)
scheduler.start()

# API endpoint to upsert vehicle payloads
@app.route("/updateVehicle", methods=["POST"])
def update_vehicle():
    data = request.get_json(force=True)
    vid = data.get("id")
    loc = data.get("location", {})
    ox = loc.get("ox"); oy = loc.get("oy")
    if not vid or ox is None or oy is None:
        return jsonify({"error": "Missing id or location.ox/oy"}), 400

    # Clean and convert types
    clean = {
        "id": vid,
        "token": data.get("token"),
        "destination": data.get("destination"),
        "GPSSpeed": float(data.get("GPSSpeed", 0)),
        "OBD2Speed": float(data.get("OBD2Speed", 0)),
        "localTimestamp": data.get("localTimestamp"),
        "heading": data.get("heading"),
        "location": {"ox": float(ox), "oy": float(oy)},
    }

    # Upsert this one vehicle
    vehicles_col.update_one({"id": vid}, {"$set": clean}, upsert=True)

    # Re‐run all simulations immediately
    monitor.mark_db_fetch_start()
    clients = list(vehicles_col.find({}, {"_id": 0}))
    monitor.mark_db_fetch_end(len(clients))

    monitor.mark_simulation_start("POST_updateVehicle")
    sim = run_simulations(clients)
    monitor.mark_simulation_end()

    rec_speed = sim["recommendedSpeed"]
    ts = datetime.datetime.utcnow().isoformat() + "Z"

    # Store the new recommendation & timestamp
    vehicles_col.update_many(
        {},
        {"$set": {"recommendedSpeed": rec_speed,
                  "lastSimulation": ts}}
    )

    monitor.finalize("results")

    # Respond with the exact format you specified
    return jsonify({
        "lastUpdated": ts,
        "message": "Vehicle data updated",
        "recommendedSpeed": rec_speed
    }), 200

@app.route("/simulationData", methods=["GET"])
def simulation_data():
    """
    Return the current recommendedSpeed plus the full list of vehicles
    in exactly the structure gui.py expects.
    """
    vehicles = list(vehicles_col.find({}, {"_id": 0}))
    if not vehicles:
        return jsonify({"error": "No vehicles in database"}), 404

    rec_speed = vehicles[0].get("recommendedSpeed")
    return jsonify({
        "recommendedSpeed": rec_speed,
        "vehicles": vehicles
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

