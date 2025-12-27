import requests
from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual import events
from textual.reactive import reactive
import time

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


class StationListItem(ListItem):
    """Custom ListItem for displaying station names."""

    def __init__(self, station_name: str):
        super().__init__()
        self.station_name = station_name

    def compose(self):
        # Mount the Label widget to this ListItem in the compose method
        yield Label(self.station_name)


class StationSelectorApp(App):
    """Textual app to interactively select a station with type-ahead search."""

    CSS_PATH = None
    stations = reactive([])

    def __init__(self, station_names):
        super().__init__()
        self.stations = sorted(station_names, key=lambda x: x.lower())
        self._search_buffer = ""
        self._search_label = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Label("Select a station (arrow keys + Enter, type to search):", id="title")
        self._search_label = Label("Search: ", id="search_label")  # Search label
        yield self._search_label
        yield ListView(*[StationListItem(name) for name in self.stations], id="station_list")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection: print station name and exit."""
        station_name = event.item.station_name
        self.exit(message=f"hello {station_name}")

    async def on_key(self, event: events.Key) -> None:
        """Allow 'q' to quit, and support type-ahead search."""
        if event.key == "q":
            self.exit()
            return

        # Handle arrow keys and Enter separately
        if event.key in ["up", "down", "enter"]:
            return  # Ignore these keys for typing buffer

        # Only consider letter/number keys and backspace for typing buffer
        if len(event.key) == 1 and event.key.isprintable() or event.key == "backspace" or event.key == "space":
            if event.key == "backspace":
                self._search_buffer = self._search_buffer[:-1]  # Remove last character
            elif event.key == "space":
                self._search_buffer += " "  # Add space to buffer
            else:
                self._search_buffer += event.key

            # Perform substring search and filter stations
            search_text = self._search_buffer.lower()
            filtered_stations = [station for station in self.stations if search_text in station.lower()]

            # Update the ListView with filtered stations
            list_view = self.query_one("#station_list", ListView)
            list_view.clear()
            list_view.extend([StationListItem(station) for station in filtered_stations])

            # Update search label
            self._search_label.update(f"Search: {self._search_buffer}")


if __name__ == "__main__":
    # Fetch datasets
    elizabeth = fetch_stop_points('elizabeth-line', 'NaptanRailStation')
    overground = fetch_stop_points('overground', 'NaptanRailStation')
    tube = fetch_stop_points('tube', 'NaptanMetroStation')
    dlr = fetch_stop_points('dlr', 'NaptanMetroStation')

    hub_common_names = fetch_transport_interchanges()

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

    # Extract station names
    station_names = [station['commonName'] for station in merged_stations]

    # Run Textual app
    app = StationSelectorApp(station_names)
    result = app.run()

    # Print result on exit
    if result:
        print(result)
