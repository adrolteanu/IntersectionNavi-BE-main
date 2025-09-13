import os
import sys
import csv
import time
import requests
from datetime import datetime
from pymongo import MongoClient
import traci
import sumolib
import xml.etree.ElementTree as ET

# Config
MONGO_URI = "mongodb://localhost:27018"
POST_URL = "http://localhost:5000/updateVehicle"
DB_NAME = "traffic_db"
COLLECTION_NAME = "vehicles"
NET_FILE = os.path.abspath("Maps/harta-automatica.net.xml")
BASE_CFG = os.path.abspath("base.sumocfg")
RESULTS_DIR = os.path.abspath("results")
ROUTE_FILE = os.path.join(RESULTS_DIR, "routes_real_time.rou.xml")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "results-analysis-time-performance/vehicle_positions_with_speed_3.csv")
MAX_REAL_SECONDS = 60
EXTRA_KMH = 20

if "SUMO_HOME" not in os.environ:
    sys.exit("❌ Please declare SUMO_HOME environment variable.")

net = sumolib.net.readNet(NET_FILE)
mongo_client = MongoClient(MONGO_URI)
vehicles_col = mongo_client[DB_NAME][COLLECTION_NAME]
clients = list(vehicles_col.find({}, {"_id": 0}))

if not clients:
    sys.exit("❌ No vehicles found in MongoDB.")

# Compute max speed (max vehicle speed + EXTRA_KMH)
max_speed_kmh = max(
    max(float(c.get("GPSSpeed", 0)), float(c.get("OBD2Speed", 0))) for c in clients
) + EXTRA_KMH
max_speed_mps = max_speed_kmh / 3.6

# Build .rou.xml dynamically
root = ET.Element("routes")
ET.SubElement(root, "vType",
              id="vehicle", vClass="delivery",
              carFollowModel="IDM", accel="2.0", decel="3.0",
              tau="1.0", minGap="2.5", maxSpeed=str(max_speed_mps))

vehicle_ids = []

for client in clients:
    vid = client["id"]
    lon = float(client["location"]["ox"])
    lat = float(client["location"]["oy"])
    x, y = net.convertLonLat2XY(lon, lat)

    edge_obj = net.getNeighboringEdges(x, y)[0][0] if net.getNeighboringEdges(x, y) else None
    if not edge_obj:
        continue

    entry_edge = edge_obj.getID()
    outs = [e.getID() for e in edge_obj.getToNode().getOutgoing() if e.getID() != entry_edge]
    exit_edge = outs[0] if outs else entry_edge

    # Depart logic
    shape = edge_obj.getShape()
    best_d = float("inf")
    departPos = 0.0
    s_accum = 0.0
    for (x1, y1), (x2, y2) in zip(shape, shape[1:]):
        dx, dy = x2 - x1, y2 - y1
        seg_len = (dx**2 + dy**2)**0.5
        if seg_len < 1e-6:
            continue
        t = ((x - x1)*dx + (y - y1)*dy) / (seg_len**2)
        t = max(0.0, min(1.0, t))
        px, py = x1 + t*dx, y1 + t*dy
        d = ((x - px)**2 + (y - py)**2)**0.5
        if d < best_d:
            best_d = d
            departPos = s_accum + ((px - x1)**2 + (py - y1)**2)**0.5
        s_accum += seg_len

    departPos = max(0.0, min(departPos, edge_obj.getLength() - 0.1))

    gps_speed = float(client.get("GPSSpeed", 0)) / 3.6
    desired_speed = min(gps_speed, max_speed_mps)
    rem_len = max(edge_obj.getLength() - departPos, 0.0)
    safe_speed = (2 * 3.0 * rem_len) ** 0.5
    depart_speed = min(desired_speed, safe_speed)

    ET.SubElement(root, "route", id=f"route_{vid}", edges=f"{entry_edge} {exit_edge}")
    ET.SubElement(root, "vehicle",
                  id=f"veh_{vid}",
                  type="vehicle",
                  route=f"route_{vid}",
                  depart="0",
                  departLane="best",
                  departSpeed=f"{depart_speed:.2f}")
    vehicle_ids.append((vid, f"veh_{vid}"))

# Save route file
os.makedirs(RESULTS_DIR, exist_ok=True)
ET.ElementTree(root).write(ROUTE_FILE, encoding="utf-8", xml_declaration=True)

# Start SUMO
sumo_cmd = ["sumo", "-c", BASE_CFG,
            "--route-files", ROUTE_FILE,
            "--start", "--no-step-log", "--quit-on-end"]
traci.start(sumo_cmd)

# CSV Logging
position_log = []

try:
    for t_real in range(1, MAX_REAL_SECONDS + 1):
        traci.simulationStep()
        for original_id, veh_id in vehicle_ids:
            if veh_id not in traci.vehicle.getIDList():
                continue
            x, y = traci.vehicle.getPosition(veh_id)
            speed = traci.vehicle.getSpeed(veh_id)
            position_log.append([t_real, veh_id, x, y, speed])

            # Send real-time update to backend
            client_info = next((c for c in clients if str(c["id"]) == str(original_id)), {})
            payload = {
                "id": original_id,
                "GPSSpeed": round(speed * 3.6, 2),
                "OBD2Speed": round(speed * 3.6, 2),
                "location": {"ox": x, "oy": y},
                "destination": client_info.get("destination", "Unknown"),
                "heading": client_info.get("heading", {"angle": 0, "orientation": "N"}),
                "localTimestamp": datetime.utcnow().isoformat() + "Z",
                "token": client_info.get("token", "defaultToken")
            }

            try:
                r = requests.post(POST_URL, json=payload)
                if r.status_code != 200:
                    print(f"❌ POST error {r.status_code} for {original_id}: {r.text}")
            except Exception as e:
                print(f"❌ POST error for {original_id}: {e}")

        time.sleep(1)

finally:
    traci.close()

# Write CSV
with open(CSV_OUTPUT, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["t_real_s", "vehicle_id", "x", "y", "speed"])
    writer.writerows(position_log)

print(f"✅ Logged to {CSV_OUTPUT}")
