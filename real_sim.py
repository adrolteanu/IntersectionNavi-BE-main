import os
import time
import glob
import requests
import subprocess

# Configs
API_URL = os.getenv("API_URL", "http://localhost:5001")
SUMO_BINARY = os.getenv("SUMO_BINARY", "sumo-gui")
SUMO_CFG = os.getenv("SUMO_CFG", "base.sumocfg")

print(f"*** RUNNING real_sim.py — real vehicle simulation (no speed limit) ***")

def get_latest_route_file():
    files = glob.glob("results/*.rou.xml")
    if not files:
        raise FileNotFoundError("No .rou.xml files found in results/")
    return max(files, key=os.path.getmtime)

def main():
    # Get vehicles from the BE
    try:
        res = requests.get(f"{API_URL}/simulationData", timeout=5)
        res.raise_for_status()
        data = res.json()
        vehicles = data.get("vehicles", [])
        print(f"[real_sim] Loaded {len(vehicles)} vehicles from backend")
    except Exception as e:
        print(f"[real_sim] ❌ Failed to fetch vehicles: {e}")
        return

    # Find last .rou.xml generated file
    try:
        route_file = get_latest_route_file()
        print(f"[real_sim] Using existing route file: {route_file}")
    except Exception as e:
        print(f"[real_sim] ❌ {e}")
        return

    # Start SUMO-GUI
    cmd = [
        SUMO_BINARY,
        "-c", SUMO_CFG,
        "--route-files", route_file,
        "--start",
        "--delay", "100"
    ]

    try:
        subprocess.Popen(cmd)
        print("[real_sim] ✅ SUMO-GUI launched with real IDM dynamics (no speed cap)")
    except Exception as e:
        print(f"[real_sim] ❌ Failed to launch SUMO-GUI: {e}")

if __name__ == "__main__":
    main()
