import xml.etree.ElementTree as ET
import json
import sys

def extract_osm_coords(osm_path, out_json="results-analysis-time-performance/locations_int.json", max_nodes=50):
    print("osm_file", osm_path)
    tree = ET.parse(osm_path)
    root = tree.getroot()

    coords = []
    for node in root.findall("node"):
        if len(coords) >= max_nodes:
            break
        lat = node.get("lat")
        lon = node.get("lon")
        if lat is None or lon is None:
            continue
        coords.append({"ox": lat, "oy": lon})

    if not coords:
        print("⚠️  No valid nodes found in", osm_path)
        return

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)

    print(f"✅  Extracted {len(coords)} coords → {out_json}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_coords.py")
        sys.exit(1)
    extract_osm_coords(sys.argv[1])
