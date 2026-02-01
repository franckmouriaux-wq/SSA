USER_ABBR = {
    'Military/Commercial': 'Dual Use'
}
MISSION_ABBR = {
    'Communications': 'Comm',
    'Earth Observation': 'EO',
    'Earth Observation/Navigation': 'EO Nav',
    'Navigation/Global Positioning': 'Nav Glo',
    'Navigation/Regional Positioning': 'Nav Reg',
    'Technology Development': 'Tech Demo'
}
import time
import math
import csv
from datetime import datetime
from skyfield.api import load, wgs84, EarthSatellite
import os

# --- Configuration ---
UCS_CSV_PATH = r'C:\Users\franc\OneDrive\Python\UCS-Satellite-Database_05012023.csv'  # Update with your actual UCS CSV file path
SPACE_TRACK_USER = 'franck.mouriaux@gmail.com'
SPACE_TRACK_PASS = 'Cc-q!YPutcM93m6'

# Abu Dhabi Location & AOI (2500km diameter, 1250km radius)
ABU_DHABI_LAT = 24.4539
ABU_DHABI_LON = 54.3773
AOI_RADIUS_KM = 1250.0
ABU_DHABI = wgs84.latlon(ABU_DHABI_LAT, ABU_DHABI_LON)


def load_ucs_data(csv_path):
    """Load UCS Satellite Database and return dict keyed by NORAD ID."""
    ucs_dict = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            norad_id = row.get('NORAD Number')
            if norad_id:
                ucs_dict[norad_id] = {
                    'Mission Type': row.get('Purpose', 'Unknown'),
                    'User Category': row.get('Users', 'Unknown')
                }
    return ucs_dict


def fetch_satellite_data():
    """Fetches all latest TLEs and metadata from Space-Track. Prints debug info."""
    from spacetrack import SpaceTrackClient
    import json
    st = SpaceTrackClient(identity=SPACE_TRACK_USER, password=SPACE_TRACK_PASS)
    ts = load.timescale()
    sat_list = []
    try:
        # Fetch all satellites, regardless of decay date or type
        print("[DEBUG] Fetching all satellites from Space-Track (no filtering, this may take a while)...")
        data = st.gp(format='json')
        if isinstance(data, str):
            print("[DEBUG] Parsing JSON string from Space-Track response...")
            data = json.loads(data)
        print(f"[DEBUG] Total objects fetched from Space-Track: {len(data)}")
        # Now filter and process only after fetching all
        for entry in data:
            obj_type = entry.get('OBJECT_TYPE', '').strip().upper()
            if obj_type in ('DEBRIS', 'ROCKET BODY'):
                continue
            try:
                sat = EarthSatellite(entry['TLE_LINE1'], entry['TLE_LINE2'], entry['OBJECT_NAME'], ts)
                sat.country = entry.get('COUNTRY_CODE', 'Unknown')
                sat.obj_type = entry.get('OBJECT_TYPE', 'Unknown')
                sat.norad_id = entry.get('NORAD_CAT_ID', None)
                sat_list.append(sat)
            except Exception as e:
                print(f"[DEBUG] Exception parsing satellite: {e}")
                continue
        print(f"[DEBUG] Finished filtering. Satellites (not debris/rocket bodies): {len(sat_list)}")
    except Exception as e:
        print(f"[DEBUG] Exception fetching satellites: {e}")
    return sat_list


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_aoi(sat, ref_time):
    subpoint = sat.at(ref_time).subpoint()
    sat_lat = subpoint.latitude.degrees
    sat_lon = subpoint.longitude.degrees
    distance = haversine(ABU_DHABI_LAT, ABU_DHABI_LON, sat_lat, sat_lon)
    return distance <= AOI_RADIUS_KM


def main():
    ts = load.timescale()
    print("Fetching UCS Satellite Database...")
    ucs_data = load_ucs_data(UCS_CSV_PATH)
    print(f"Loaded {len(ucs_data)} UCS satellites.")
    print("Fetching satellite data from Space-Track... (this may take a while)")
    satellites = fetch_satellite_data()
    print(f"Fetched {len(satellites)} satellites from Space-Track.")
    time.sleep(2)
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            now = ts.now()
            print(f"Satellites currently over UAE (within 1250km of Abu Dhabi):\n")
            print("Note: This list excludes debris and rocket bodies.\n")
            print(f"Total satellites fetched: {len(satellites)}\n")
            print(f"{'NAME':<25} | {'COUNTRY':<10} | {'TYPE':<12} | {'MISSION':<15} | {'USER':<15} | {'ALT(km)':>8} | {'LAT':>8} | {'LON':>9}")
            print("-" * 130)
            count = 0
            for sat in satellites:
                if is_within_aoi(sat, now):
                    subpoint = sat.at(now).subpoint()
                    lat = subpoint.latitude.degrees
                    lon = subpoint.longitude.degrees
                    alt = subpoint.elevation.km
                    country = sat.country if sat.country is not None else "Unknown"
                    obj_type = sat.obj_type if hasattr(sat, 'obj_type') and sat.obj_type is not None else "Unknown"
                    norad_id = str(sat.norad_id) if sat.norad_id is not None else None
                    mission_full = ucs_data.get(norad_id, {}).get('Mission Type', 'Unknown')
                    if not mission_full or mission_full.strip() == '':
                        mission_full = 'Unknown'
                    mission = MISSION_ABBR.get(mission_full, mission_full)
                    user_full = ucs_data.get(norad_id, {}).get('User Category', 'Unknown')
                    if not user_full or user_full.strip() == '':
                        user_full = 'Unknown'
                    user = USER_ABBR.get(user_full, user_full)
                    print(f"{sat.name[:25]:<25} | {country:<10} | {obj_type:<12} | {mission:<15} | {user:<15} | {alt:8.1f} | {lat:8.3f} | {lon:9.3f}")
                    count += 1
            if count == 0:
                print("No satellites currently in area.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
