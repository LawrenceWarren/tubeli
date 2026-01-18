import requests
import re
from json import dumps as json_dumps
from collections import defaultdict
import re

API_URL = "https://api.tfl.gov.uk"

MAX_ARRIVALS_PER_DIRECTION = 5

ELIZABETH_LINE_DETAILS = {
    "elizabeth": {
        "id": "elizabeth",
        "name": "Elizabeth Line",
        "color": "#60399E",
        "text_color": "#fff",
    },
}
DLR_LINE_DETAILS = {
    "dlr": {
        "id": "dlr",
        "name": "DLR",
        "color": "#00AFAD",
        "text_color": "#000",
    }
}
TUBE_LINE_DETAILS = {
    "central": {
        "id": "central",
        "name": "Central",
        "color": "#DC241F",
        "text_color": "#fff",
    },
    "jubilee": {
        "id": "jubilee",
        "name": "Jubilee",
        "color": "#838D93",
        "text_color": "#000",
    },
    "northern": {
        "id": "northern",
        "name": "Northern",
        "color": "#000000",
        "text_color": "#fff",
    },
    "district": {
        "id": "district",
        "name": "District",
        "color": "#007D32",
        "text_color": "#fff",
    },
    "circle": {
        "id": "circle",
        "name": "Circle",
        "color": "#FFC80A",
        "text_color": "#000",
    },
    "hammersmith-city": {
        "id": "hammersmith-city",
        "name": "Hammersmith & City",
        "color": "#F589A6",
        "text_color": "#000",
    },
    "waterloo-city": {
        "id": "waterloo-city",
        "name": "Waterloo & City",
        "color": "#76D0BD",
        "text_color": "#000",
    },
    "metropolitan": {
        "id": "metropolitan",
        "name": "Metropolitan",
        "color": "#9B0058",
        "text_color": "#fff",
    },
    "bakerloo": {
        "id": "bakerloo",
        "name": "Bakerloo",
        "color": "#B26300",
        "text_color": "#000",
    },
    "victoria": {
        "id": "victoria",
        "name": "Victoria",
        "color": "#039BE5",
        "text_color": "#000",
    },
    "piccadilly": {
        "id": "piccadilly",
        "name": "Piccadilly",
        "color": "#0019A8",
        "text_color": "#fff",
    },
}
OVERGROUND_LINE_DETAILS = {
    "weaver": {
        "id": "weaver",
        "name": "Weaver",
        "color": "#823A62",
        "text_color": "#fff",
    },
    "liberty": {
        "id": "liberty",
        "name": "Liberty",
        "color": "#5D6061",
        "text_color": "#fff",
    },
    "mildmay": {
        "id": "mildmay",
        "name": "Mildmay",
        "color": "#0077AD",
        "text_color": "#fff",
    },
    "windrush": {
        "id": "windrush",
        "name": "Windrush",
        "color": "#ED1B00",
        "text_color": "#000",
    },
    "lioness": {
        "id": "lioness",
        "name": "Lioness",
        "color": "#FAA61A",
        "text_color": "#000",
    },
    "suffragette": {
        "id": "suffragette",
        "name": "Suffragette",
        "color": "#5BBB72",
        "text_color": "#000",
    },
}
LINE_DETAILS = (
    ELIZABETH_LINE_DETAILS
    | DLR_LINE_DETAILS
    | TUBE_LINE_DETAILS
    | OVERGROUND_LINE_DETAILS
)

CFOT = "check-front-of-train"

ALL_STATION_DATA: list = []
displayed_station_data: list = []
search_buffer: str = ""


def get_all_line_details():
    """
    Returns: LINE_DETAILS
    """
    return LINE_DETAILS


def get_line_details_by_id(id):
    return LINE_DETAILS[id]


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


def sanitise_stop_points(stop_points, mode, stop_type=None):
    """Takes a list of stop points as fetched from the API, and returns a sanitised list"""
    result = []

    for sp in stop_points:
        if sp["stopType"] != stop_type and stop_type:
            continue
        lines = simplify_lines(sp.get('lines', []))
        station = {
            'commonName': station_name_filter(sp['commonName']),
            'lines': lines,
            'id': sp['id'],
            'mode': mode,
        }
        if 'hubNaptanCode' in sp:
            station['hubId'] = sp['hubNaptanCode']
        result.append(station)
    return result


def fetch_stop_points_by_line(line_id, mode):
    """Fetch all StopPoints for a given line ID, returning simplified station dicts."""
    response = requests.get(f"{API_URL}/Line/{line_id}/StopPoints")
    response.raise_for_status()
    stop_points = response.json()
    return sanitise_stop_points(stop_points, mode)


def fetch_stop_points_by_mode(mode, stop_type):
    """Fetch all StopPoints for a given mode, returning simplified station dicts."""
    response = requests.get(f"{API_URL}/StopPoint/Mode/{mode}")
    response.raise_for_status()
    data = response.json()
    stop_points = data.get('stopPoints', [])
    return sanitise_stop_points(stop_points, mode, stop_type)


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
        if line['id'] in LINE_DETAILS.keys()
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

    for stations in station_lists:
        for station in stations:
            s_id = station.get("hubId") or station["id"]

            if s_id not in station_map:
                station_map[s_id] = station
                station_map[s_id]["modes"] = {station["mode"]: station["id"]}
                del station_map[s_id]["mode"]
            else:
                existing = station_map[s_id]
                existing["lines"] = merge_lines(
                    existing["lines"], station["lines"]
                )
                existing["modes"][station["mode"]] = station["id"]

    for station in station_map.values():
        if 'hubId' in station and station['hubId'] in hub_common_names:
            station['commonName'] = hub_common_names[station['hubId']]

    return list(station_map.values())


def parse_direction(arrival):
    DIRECTIONS = ["north", "south", "east", "west"]
    if "platformName" in arrival and arrival["platformName"]:
        for d in DIRECTIONS:
            if d in arrival["platformName"].lower():
                return f"{d}bound"

    return (
        arrival["direction"]
        if "direction" in arrival and arrival["direction"]
        else "terminal"
    )


def construct_arrival(arrival, station_id):
    destination_id = (
        arrival["destinationNaptanId"]
        if "destinationNaptanId" in arrival
        else CFOT
    )

    if destination_id == station_id:
        return None

    destination_name = (
        clean_station_name(arrival["destinationName"])
        if "destinationName" in arrival
        else "Check train"
    )

    return {
        "destination_id": destination_id,
        "destination_name": destination_name,
        "expected_time": arrival["expectedArrival"],
        "platform_name": arrival["platformName"],
    }


def fetch_line_arrivals(station_id):
    response = requests.get(f"{API_URL}/StopPoint/{station_id}/Arrivals")
    response.raise_for_status()
    arrivals = sorted(response.json(), key=lambda x: x["expectedArrival"])

    lines = {}

    for arrival in arrivals:
        line_id = arrival["lineId"]

        if line_id not in lines:
            lines[line_id] = {
                "line_name": arrival["lineName"],
                "arrivals": {},
            }

        direction = parse_direction(arrival)

        if direction == "terminal":
            continue

        if direction not in lines[line_id]["arrivals"]:
            lines[line_id]["arrivals"][direction] = []

        a = construct_arrival(arrival, station_id)

        if (
            a is not None
            and len(lines[line_id]["arrivals"][direction])
            < MAX_ARRIVALS_PER_DIRECTION
        ):
            lines[line_id]["arrivals"][direction].append(a)

    return lines


def clean_station_name(name: str) -> str:
    # 1️⃣ Remove standard suffixes
    suffixes = [" DLR Station", " Underground Station", " Rail Station"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[: -len(suffix)]

    # 2️⃣ Remove bracketed substrings except "(Olympia)"
    # Match: space + '(' + anything except ')' + ')'
    # Negative lookahead for "Olympia"
    pattern = r' \((?!Olympia\)).*?\)'
    name = re.sub(pattern, "", name)

    # 3️⃣ Trim whitespace
    return name.strip()


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


def fetch_station_arrivals(result):
    merged_arrivals = {}

    for mode in result["modes"]:
        merged_arrivals |= fetch_line_arrivals(result["modes"][mode])

    return merged_arrivals


def identify_lines_directions(merged_arrivals):
    result = {}

    for line_id, line_data in merged_arrivals.items():
        directions = defaultdict(dict)

        for terminal_id, terminal_data in line_data.get(
            "terminals", {}
        ).items():
            arrivals = terminal_data.get("arrivals", [])

            if not arrivals:
                continue

            direction = arrivals[0].get("direction")
            station_name = terminal_data.get("station_name")

            if direction and station_name:
                directions[direction][terminal_id] = station_name

        result[line_id] = {
            "line_name": line_data.get("line_name"),
            "directions": dict(directions),
        }

    return result


def fetch_line_status(line_id):
    result = {}

    response = requests.get(f"{API_URL}/Line/{line_id}/Status?detail=true")
    response.raise_for_status()
    full_statuses = response.json()[0]

    result["id"] = full_statuses["id"]
    result["name"] = full_statuses["name"]

    result["statuses"] = []

    for ls in full_statuses["lineStatuses"]:
        if ls["statusSeverity"] == 10:
            continue
        status = {}
        status["summary"] = ls["statusSeverityDescription"]
        status["reason"] = ls["reason"]

        affected_stops = []

        for stop in ls["disruption"]["affectedStops"]:
            affected_stops.append(stop["naptanId"])

        status["affected_stops"] = affected_stops

        result["statuses"].append(status)

    return result
