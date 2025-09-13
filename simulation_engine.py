import os
import sys
import socket
import xml.etree.ElementTree as ET
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
import traci
import sumolib

# Parameters 
START_SPEED = 15    # km/h
END_SPEED   = 60    # km/h
SPEED_STEP  = 5     # km/h 

if "SUMO_HOME" not in os.environ:
    sys.exit("Please declare SUMO_HOME")

# Network
NET_FILE = os.path.abspath(os.path.join(os.getcwd(), "intrare-automatica.net.xml"))
NET = sumolib.net.readNet(NET_FILE)

def get_free_port():
    s = socket.socket()
    s.bind(("", 0))
    _, port = s.getsockname()
    s.close()
    return port

def find_nearest_edge(x, y):
    best_edge = None
    best_d2 = float("inf")
    for edge in NET.getEdges():
        shape = edge.getShape()
        for (x1, y1), (x2, y2) in zip(shape, shape[1:]):
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                continue
            t = ((x - x1)*dx + (y - y1)*dy) / (dx*dx + dy*dy)
            t = max(0.0, min(1.0, t))
            px, py = x1 + t*dx, y1 + t*dy
            d2 = (x - px)**2 + (y - py)**2
            if d2 < best_d2:
                best_d2 = d2
                best_edge = edge
    return best_edge

def build_route_file(max_speed_kmh, clients):
    print("SUNT AICIIIII")
    root = ET.Element("routes")
    max_speed_mps = max_speed_kmh / 3.6

    # vType
    ET.SubElement(root, "vType",
                  id="vehicle", vClass="delivery",
                  carFollowModel="IDM", accel="2.0", decel="3.0",
                  tau="1.0", minGap="2.5", maxSpeed=str(max_speed_mps))

    for client in clients:
        vid = client["id"]
        lon = float(client["location"]["ox"])
        lat = float(client["location"]["oy"])
        x, y = NET.convertLonLat2XY(lon, lat)

        # Find nearest edge
        nbrs = NET.getNeighboringEdges(x, y)
        edge_obj = nbrs[0][0] if nbrs else find_nearest_edge(x, y)
        if edge_obj is None:
            print(f"⚠️ Skipping {vid}: no nearby edge found!")
            continue

        entry_edge = edge_obj.getID()

        # Pick exit edge
        outs = [e.getID() for e in edge_obj.getToNode().getOutgoing() if e.getID() != entry_edge]
        exit_edge = random.choice(outs) if outs else entry_edge

        # Compute accurate departPos
        shape = edge_obj.getShape()
        best_d = float("inf")
        departPos = 0.0
        s_accum = 0.0
        for (x1, y1), (x2, y2) in zip(shape, shape[1:]):
            dx, dy = x2 - x1, y2 - y1
            seg_len = (dx*dx + dy*dy)**0.5
            if seg_len < 1e-6:
                continue
            t = ((x - x1)*dx + (y - y1)*dy) / (seg_len*seg_len)
            t = max(0.0, min(1.0, t))
            px, py = x1 + t*dx, y1 + t*dy
            d = ((x - px)**2 + (y - py)**2)**0.5
            if d < best_d:
                best_d = d
                departPos = s_accum + ((px - x1)**2 + (py - y1)**2)**0.5
            s_accum += seg_len

        departPos = min(departPos, edge_obj.getLength() - 0.1)
        if departPos < 0:
            departPos = 0.0

        # Vehicle depart speed: clipped to both maxSpeed and safe braking distance
        gps_speed_kmh = float(client["GPSSpeed"])
        gps_speed_mps = gps_speed_kmh / 3.6
        desired_speed = min(gps_speed_mps, max_speed_mps)

        rem_len = max(edge_obj.getLength() - departPos, 0.0)
        decel = 3.0
        safe_speed = (2 * decel * rem_len) ** 0.5

        depart_speed = min(desired_speed, safe_speed)

        # Write route and vehicle
        ET.SubElement(root, "route", id=f"route_{vid}", edges=f"{entry_edge} {exit_edge}")
        ET.SubElement(root, "vehicle",
                      id=f"veh_{vid}",
                      type="vehicle",
                      route=f"route_{vid}",
                      depart="0",
                      departPos=f"{departPos:.2f}",
                      departLane="best",
                      departSpeed=f"{depart_speed:.2f}")

    # Save
    results_dir = os.path.abspath(os.path.join(os.getcwd(), "results"))
    os.makedirs(results_dir, exist_ok=True)
    rou_path = os.path.join(results_dir, f"routes_sim_{max_speed_kmh}.rou.xml")
    ET.ElementTree(root).write(rou_path, encoding="utf-8", xml_declaration=True)

    cnt = len(root.findall("vehicle"))
    print(f">>> [DEBUG] Generated {cnt} <vehicle> entries in {rou_path}")
    if cnt == 0:
        print(">>> ⚠️ No vehicles generated!")

    return rou_path

def run_single_simulation_route(max_speed, route_file):
    tripinfo_file = route_file.replace("routes_sim", "tripinfo_sim").replace(".rou.xml", ".xml")
    # ensure we start from scratch
    if os.path.exists(tripinfo_file):
        os.remove(tripinfo_file)

    cfg = os.path.abspath(os.path.join(os.getcwd(), "base.sumocfg"))
    sumo_cmd = [
        "sumo", "-c", cfg,
        "--no-warnings", "--no-step-log",
        "--route-files", route_file,
        "--tripinfo-output", tripinfo_file,
        "--quit-on-end"
    ]

    port = get_free_port()
    traci.start(sumo_cmd, port=port)
    try:
        while traci.simulation.getTime() < 3600.0:
            traci.simulationStep()
    finally:
        traci.close()

    # Safe‐parse the tripinfo output
    waiting_times = []
    vehicles_arrived = 0

    if not os.path.exists(tripinfo_file):
        print(f"⚠️  No tripinfo output for speed={max_speed} (file missing), skipping parse.")
        return max_speed, waiting_times, vehicles_arrived

    try:
        tree = ET.parse(tripinfo_file)
        for trip in tree.getroot().findall("tripinfo"):
            wt = trip.get("waitingTime")
            if wt:
                waiting_times.append(float(wt))
            vehicles_arrived += 1
    except ET.ParseError:
        print(f"⚠️  Could not parse {tripinfo_file}, skipping.")

    return max_speed, waiting_times, vehicles_arrived


def run_simulations(clients,
                    sumo_binary: str = "sumo",
                    config_file: str = "base.sumocfg"):
    """
    clients       – list of vehicle dicts
    sumo_binary   – "sumo" or "sumo-gui"
    config_file   – .sumocfg path
    """
    speeds = list(range(START_SPEED, END_SPEED+1, SPEED_STEP))

    # Build all the route files first
    route_files = {s: build_route_file(s, clients) for s in speeds}

    results = {}
    throughputs = {}
    with ProcessPoolExecutor(max_workers=len(speeds)) as executor:
        futures = {
            executor.submit(run_single_simulation_route, s, route_files[s]): s
            for s in speeds
        }
        for f in as_completed(futures):
            s, waiting_times, vehicles_arrived = f.result()
            results[s] = waiting_times
            throughputs[s] = vehicles_arrived

    summed_wait = {s: sum(results[s]) for s in speeds}
    best = min(summed_wait, key=lambda s: summed_wait[s])

    print(f">>> 🚗 Vehicles simulated: {len(clients)}\n")
    for s in speeds:
        print(f"🚗 Throughput for {s} km/h: {throughputs[s]} vehicles")
        print(f"🕒 Total waiting time for {s} km/h: {summed_wait[s]:.2f} seconds")
    print(f"\n>>> 🏁 Recommended speed: {best} km/h\n")

    return {"recommendedSpeed": f"{best} km/h"}
