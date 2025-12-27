import requests
import json

API_URL = "https://api.tfl.gov.uk"

LINE_ID = [
    "central",
    "jubilee",
    "northern",
    "district",
    "circle",
    "hammersmith-city",
    "waterloo-city",
    "metropolitan",
    "bakerloo",
    "victoria",
    "piccadilly",
    "weaver",
    "liberty",
    "mildmay",
    "windrush",
    "lioness",
    "suffragette",
    "elizabeth",
    "dlr",
]


def fetch_stop_points(mode, stop_type):
    """Fetch StopPoints for a given mode and stopType, returning simplified station dicts."""
    response = requests.get(f"{API_URL}/StopPoint/Mode/{mode}")
    response.raise_for_status()
    data = response.json()
    stop_points = data.get('stopPoints', [])

    result = []
    for sp in stop_points:
        if sp.get('stopType') != stop_type:
            continue
        lines = simplify_lines(sp.get('lines', []))
        station = {'commonName': sp['commonName'], f'{mode}Id': sp['id'], 'lines': lines}
        # Add hubId if it exists
        if 'hubNaptanCode' in sp:
            station['hubId'] = sp['hubNaptanCode']
        result.append(station)
    return result


def fetch_transport_interchanges():
    """Fetch all TransportInterchange StopPoints and return {hubId: commonName} mapping."""
    response = requests.get(f"{API_URL}/StopPoint/Type/TransportInterchange")
    response.raise_for_status()
    stop_points = response.json()
    return {sp['id']: sp['commonName'] for sp in stop_points}


def simplify_lines(lines):
    """Filter lines to allowed LINE_IDs and return sorted list of dicts {line_id, line_name}."""
    filtered = [{'line_id': line['id'], 'line_name': line['name']} for line in lines if line['id'] in LINE_ID]
    return sorted(filtered, key=lambda x: x['line_name'])


def merge_lines(existing_lines, new_lines):
    """Merge two lists of lines, deduplicating by line_id."""
    existing_ids = {line['line_id'] for line in existing_lines}
    return existing_lines + [line for line in new_lines if line['line_id'] not in existing_ids]


def merge_stations(station_lists, preference_order, hub_common_names):
    """
    Merge station lists on hubId or ID.

    Preference for commonName is:
        - hub commonName (if hubId present)
        - else first available by preference_order
    """
    station_map = {}

    for mode_label, stations in station_lists:
        id_field = f'{mode_label}Id'
        for station in stations:
            key = station.get('hubId') or station[id_field]

            if key not in station_map:
                station_map[key] = station
            else:
                existing = station_map[key]

                # Merge lines
                existing['lines'] = merge_lines(existing['lines'], station['lines'])

                # Merge IDs
                existing[id_field] = station[id_field]

                # Merge commonName based on preference order
                for preferred_mode in preference_order:
                    preferred_id_field = f'{preferred_mode}Id'
                    if preferred_id_field in station and preferred_id_field not in existing:
                        existing[preferred_id_field] = station[preferred_id_field]

    # Override commonName with hub commonName if possible
    for station in station_map.values():
        if 'hubId' in station and station['hubId'] in hub_common_names:
            station['commonName'] = hub_common_names[station['hubId']]
        else:
            # Fallback: prefer commonName by defined mode order
            for mode in preference_order:
                id_field = f'{mode}Id'
                if id_field in station:
                    break  # first mode with an ID already retains its commonName

    return list(station_map.values())


if __name__ == "__main__":
    # Fetch datasets
    elizabeth = fetch_stop_points('elizabeth-line', 'NaptanRailStation')
    overground = fetch_stop_points('overground', 'NaptanRailStation')
    tube = fetch_stop_points('tube', 'NaptanMetroStation')
    dlr = fetch_stop_points('dlr', 'NaptanMetroStation')

    # Fetch TransportInterchange hub names
    hub_common_names = fetch_transport_interchanges()

    # Merge datasets with commonName preference: hub > elizabeth > overground > tube > dlr
    merged_stations = merge_stations(
        station_lists=[
            ('elizabeth-line', elizabeth),
            ('overground', overground),
            ('tube', tube),
            ('dlr', dlr),
        ],
        preference_order=['elizabeth-line', 'overground', 'tube', 'dlr'],
        hub_common_names=hub_common_names,
    )

    # Output JSON
    print(json.dumps(merged_stations, indent=2))
