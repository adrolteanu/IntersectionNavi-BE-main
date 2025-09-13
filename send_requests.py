import time
import requests
import random
import uuid
import json
from datetime import datetime

API_URL = "http://localhost:5001"
LOCATIONS_FILE = "locations/locations_int.json"

def load_coords():
    with open(LOCATIONS_FILE, "r") as f:
        return json.load(f)

def generate_payload(coord):
    vehicle_id = str(uuid.uuid4())
    payload = {
        "id": vehicle_id,
        "token": "someAuthToken",
        "location": {
            "ox": str(coord["ox"]),
            "oy": str(coord["oy"])
        },
        "GPSSpeed": str(random.randint(30, 70)),
        "OBD2Speed": str(round(random.uniform(50, 70), 2)),
        "localTimestamp": datetime.utcnow().isoformat() + "Z",
        "heading": {
            "angle": random.choice([0, 45, 90, 135, 180, 225, 270, 315]),
            "orientation": random.choice(["N", "S", "E", "W"])
        }
    }
    return vehicle_id, payload

def send_loop():
    coords = load_coords()
    print("[SEND] 🚀 Starting POST loop every 30s...")
    while True:
        coord = random.choice(coords)
        vehicle_id, payload = generate_payload(coord)

        try:
            r = requests.post(f"{API_URL}/updateVehicle", json=payload)
            if r.status_code == 200:
                print(f"[SEND] ✅ Added vehicle '{vehicle_id}', server: {r.json()}")
            else:
                print(f"[SEND] ❌ Failed to POST vehicle: {r.status_code} {r.text}")
        except Exception as e:
            print(f"[SEND] ❌ Exception while sending POST: {e}")

        time.sleep(30)

if __name__ == "__main__":
    send_loop()
