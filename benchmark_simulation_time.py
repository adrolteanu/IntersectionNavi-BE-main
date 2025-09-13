import os
import time
import traci
import csv

# Config
SUMO_BINARY = "sumo"
CONFIG_FILE = "base.sumocfg"
ROUTE_FILE = "results/routes_sim_20.rou.xml"
RESULT_CSV = "results-analysis-time-performance/simulation_duration_20km_int.csv"

START_SIM_TIME = 0
END_SIM_TIME = 3600
STEP = 10
SIMULATED_TIMES = [1240, 1540, 1810, 1820, 2070, 2300, 2310, 2520, 2730, 2930, 3130, 3310, 3490]


def run_benchmark():
    results = []

    # Running simulations
    for sim_time in range(START_SIM_TIME, END_SIM_TIME + 10, STEP):
        sumo_cmd = [
            SUMO_BINARY, "-c", CONFIG_FILE,
            "--no-warnings", "--no-step-log",
            "--route-files", ROUTE_FILE,
            "--begin", "0",
            "--end", str(sim_time),
            "--quit-on-end"
        ]

        print(f"▶️ Running simulation for {sim_time} seconds...")
        start_time = time.time()
        traci.start(sumo_cmd)
        try:
            while traci.simulation.getTime() < sim_time:
                traci.simulationStep()
        finally:
            traci.close()
        end_time = time.time()

        real_time = round(end_time - start_time, 3)
        results.append([sim_time, real_time])
        print(f"✅ {sim_time}s simulated in {real_time}s real time")

    # Write results to CSV
    with open(RESULT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SimulatedTime(s)", "RealTime(s)"])
        writer.writerows(results)

    print(f"\n📁 Results saved to {RESULT_CSV}")

if __name__ == "__main__":
    run_benchmark()
