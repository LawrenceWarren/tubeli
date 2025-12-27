import requests
import re
from json import dumps as json_dumps
from textual import log

API_URL = "https://api.tfl.gov.uk"

ARRIVALS_PER_TERMINAL = 5

ELIZABETH_LINE_IDS = ["elizabeth"]
DLR_LINE_IDS = ["dlr"]
TUBE_LINE_IDS = [
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
]
OVERGROUND_LINE_IDS = [
    "weaver",
    "liberty",
    "mildmay",
    "windrush",
    "lioness",
    "suffragette",
]

LINE_IDS = (
    ELIZABETH_LINE_IDS + DLR_LINE_IDS + TUBE_LINE_IDS + OVERGROUND_LINE_IDS
)

ALL_STATION_DATA: list = []
displayed_station_data: list = []
search_buffer: str = ""


def set_all_station_data(d: list) -> None:
    global ALL_STATION_DATA
    ALL_STATION_DATA = d


def get_all_station_data() -> list:
    return ALL_STATION_DATA


def set_filtered_station_data(d: list) -> None:
    global displayed_station_data
    displayed_station_data = d


def get_filtered_station_data() -> list:
    return displayed_station_data


def station_name_filter(name):
    pattern = r'\s* (DLR Station|Rail Station|Underground Station|Station)\s*$'
    return re.sub(pattern, '', name, flags=re.IGNORECASE)


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
        station = {
            'commonName': station_name_filter(sp['commonName']),
            f'{mode}Id': sp['id'],
            'lines': lines,
        }
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
    filtered = [
        {'line_id': line['id'], 'line_name': line['name']}
        for line in lines
        if line['id'] in LINE_IDS
    ]
    return sorted(filtered, key=lambda x: x['line_name'])


def merge_lines(existing_lines, new_lines):
    """Merge two lists of lines, deduplicating by line_id."""
    existing_ids = {line['line_id'] for line in existing_lines}
    return existing_lines + [
        line for line in new_lines if line['line_id'] not in existing_ids
    ]


def merge_stations(station_lists, hub_common_names):
    """Merge station lists on hubId or ID."""
    station_map = {}

    for mode_label, stations in station_lists:
        id_field = f'{mode_label}Id'
        for station in stations:
            key = station.get('hubId') or station[id_field]

            if key not in station_map:
                station_map[key] = station
            else:
                existing = station_map[key]
                existing['lines'] = merge_lines(
                    existing['lines'], station['lines']
                )
                existing[id_field] = station[id_field]

    for station in station_map.values():
        if 'hubId' in station and station['hubId'] in hub_common_names:
            station['commonName'] = hub_common_names[station['hubId']]

    return list(station_map.values())


def fetch_arrivals(station_id, line_id):
    response = requests.get(f"{API_URL}/StopPoint/{station_id}/Arrivals")
    response.raise_for_status()

    # TODO: For terminal stations, maybe just show timetable data?
    # /Line/{id}/Timetable/{fromStopPointId}
    arrivals = sorted(response.json(), key=lambda x: x["expectedArrival"])

    terminals = {}

    for arrival in arrivals:
        destination_id = arrival["destinationNaptanId"]
        destination_name = arrival["destinationName"]
        filtered_arrival = {
            "expected_time": arrival["expectedArrival"],
            "platform_name": arrival.get("platformName"),
            "direction": arrival["direction"],
        }

        if destination_id not in terminals:
            terminals[destination_id] = {
                "station_name": destination_name,
                "arrivals": [],
            }
            if destination_id == station_id:
                print(
                    "TODO: This station is a terminal - find a way to find the times!"
                )

        if len(terminals[destination_id]["arrivals"]) < ARRIVALS_PER_TERMINAL:
            terminals[destination_id]["arrivals"].append(filtered_arrival)
        else:
            continue

    return terminals


def handle_key_press(key: str) -> list:
    global search_buffer, displayed_station_data, ALL_STATION_DATA

    if key in ["up", "down", "enter"]:
        return "", []

    if len(key) == 1 and key.isprintable():
        search_buffer += key
    elif key == "backspace" and search_buffer:
        search_buffer = search_buffer[:-1]
        displayed_station_data = ALL_STATION_DATA
    elif key == "space":
        search_buffer += " "

    displayed_station_data = [
        d
        for d in displayed_station_data
        if search_buffer.lower() in d['commonName'].lower()
    ]

    return search_buffer, displayed_station_data
