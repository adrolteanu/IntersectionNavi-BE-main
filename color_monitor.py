import traci
import time
import os

RECOMMENDED_SPEED_KMH = int(os.getenv("RECOMMENDED_SPEED", "50"))
TRACI_PORT = int(os.getenv("TRACI_PORT", "8813"))

recommended_speed = RECOMMENDED_SPEED_KMH / 3.6  # convert to m/s

def set_vehicle_colors():
    for veh_id in traci.vehicle.getIDList():
        try:
            current_speed = traci.vehicle.getSpeed(veh_id)
            if abs(current_speed - recommended_speed) < 0.1:
                traci.vehicle.setColor(veh_id, (0, 0, 255, 255))  # Blue
            elif current_speed < recommended_speed:
                traci.vehicle.setColor(veh_id, (0, 255, 0, 255))  # Green
            else:
                traci.vehicle.setColor(veh_id, (255, 0, 0, 255))  # Red
        except traci.TraCIException:
            continue

if __name__ == "__main__":
    traci.init(TRACI_PORT)
    print(f"[COLOR] Connected to SUMO-GUI at port {TRACI_PORT} with RECOMMENDED_SPEED={RECOMMENDED_SPEED_KMH} km/h")

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        set_vehicle_colors()
        time.sleep(0.1)

    traci.close()
    print("[COLOR] Finished coloring vehicles.")
