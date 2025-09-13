import pandas as pd
from sumolib.net import readNet

# Files
csv_input = "results-analysis-time-performance/vehicle_positions_with_speed_2.csv"
csv_output = "results-analysis-time-performance/vehicule_latlon.csv"
net_file = "Maps/harta-automatica.net.xml" 

# Loading SUMO
net = readNet(net_file)

# Read from CSV files
df = pd.read_csv(csv_input)

# Convert
def to_latlon(row):
    lat, lon = net.convertXY2LonLat(row["x"], row["y"])
    return pd.Series({"lat": lat, "lon": lon})

# Transform
df[["lat", "lon"]] = df.apply(to_latlon, axis=1)

# Save
df.to_csv(csv_output, index=False)
print(f"Coordinates lat/lon saved in {csv_output}")
