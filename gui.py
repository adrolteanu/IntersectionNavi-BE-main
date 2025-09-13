import os
import json
import uuid
import time
import random
import requests
import subprocess
from datetime import datetime

from simulation_engine import build_route_file 

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:5001")
SUMO_BINARY = os.getenv("SUMO_BINARY", "sumo-gui")
SUMO_CFG = os.getenv("SUMO_CFG", "base.sumocfg")
POLL_INTERVAL = 30  # seconds
COORD_FILE = "locations/locations.json"

print(f"*** RUNNING gui.py — polling every {POLL_INTERVAL} s ***")

# Load coordinates list
if not os.path.exists(COORD_FILE):
    raise FileNotFoundError(f"Missing {COORD_FILE} with valid coordinates.")
with open(COORD_FILE, "r") as f:
    coords = json.load(f)

if not coords or len(coords) < 1:
    raise ValueError("Coordinate list is empty.")

last_speed = None

while True:
    try:
        # Get current recommendation
        res = requests.get(f"{API_URL}/simulationData", timeout=5)
        if res.status_code != 200:
            print(f"[GUI] Server error: {res.status_code}")
            time.sleep(POLL_INTERVAL)
            continue

        data = res.json()
        rec_speed = data.get("recommendedSpeed")
        if rec_speed is None:
            print("[GUI] No recommendation yet.")
            time.sleep(POLL_INTERVAL)
            continue

        # New recommendation
        if rec_speed != last_speed:
            print(f"[GUI] Detected new recommendedSpeed={rec_speed} (was {last_speed}) — re-running GUI")
            last_speed = rec_speed

            # Regenerate route file
            vehicles = requests.get(f"{API_URL}/simulationData").json().get("vehicles", [])
            speed_int = int(rec_speed.replace(" km/h", ""))
            route_file = build_route_file(speed_int, vehicles)
            print(f"[GUI] Generated {len(vehicles)} vehicles @ {rec_speed} → {route_file}")

            # Pick a random available port
            random_port = random.randint(8800, 8899)

            # Launch SUMO-GUI
            cmd = [
                SUMO_BINARY,
                "-c", SUMO_CFG,
                "--route-files", route_file,
                "--start",
                "--delay", "100",
                "--remote-port", str(random_port)
            ]
            subprocess.Popen(cmd)
            print(f"[GUI] Launched SUMO-GUI on port {random_port}")

            # Step 6: Launch color monitor in parallel
            color_env = os.environ.copy()
            color_env["RECOMMENDED_SPEED"] = str(speed_int)
            color_env["TRACI_PORT"] = str(random_port)
            subprocess.Popen(["python", "color_monitor.py"], env=color_env)
            print(f"[GUI] Launched color monitor for port {random_port} with RECOMMENDED_SPEED={speed_int} km/h")

        else:
            print(f"[GUI] No change in recommendedSpeed: still {rec_speed}")

    except Exception as e:
        print(f"[GUI] 🔥 GUI engine error: {e}")

    time.sleep(POLL_INTERVAL)
