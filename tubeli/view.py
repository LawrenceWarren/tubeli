from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Container
from textual.screen import Screen
from textual import events
from textual.reactive import reactive
from textual.widgets import Pretty

from model import (
    handle_key_press,
    set_all_station_data,
    set_filtered_station_data,
    get_line_details_by_id,
    build_merged_arrivals,
    identify_lines_directions,
)


class LineListItem(ListItem):
    """Custom ListItem for displaying line names."""

    def __init__(self, line_info):
        super().__init__()
        self.line_info = line_info  # Map

    def compose(self):
        label = Label(self.line_info["name"], id="line-list-item")
        label.styles.background = self.line_info["color"]
        label.styles.color = self.line_info["text_color"]
        yield label


class StationListItem(ListItem):
    """Custom ListItem for displaying station names."""

    def __init__(self, station_info, station_name_column_width):
        super().__init__()
        self.station_info = station_info
        self.station_name_column_width = station_name_column_width

    def compose(self):
        name = self.station_info["commonName"]
        lines = []

        for line in self.station_info['lines']:
            info = get_line_details_by_id(line['line_id'])
            lab = Label(info["name"])
            lab.styles.background = info["color"]
            lab.styles.color = info["text_color"]
            lines.append(lab)

        station_name = Label(name)
        padding = self.station_name_column_width - len(name)
        station_name.styles.padding = (0, padding, 0, 0)
        yield Container(
            station_name,
            *lines,
            id="station-list-item",
        )


class PlatformSelectorScreen(Screen):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, station_info):
        super().__init__()
        self.station_info = station_info
        self.merged_arrivals = build_merged_arrivals(station_info)
        self.line_directions = identify_lines_directions(self.merged_arrivals)

    def compose(self) -> ComposeResult:
        for _, line in self.line_directions.items():
            yield Label(line["line_name"])
            for direction in line["directions"].keys():
                yield Label(direction)
                # TODO: Yield this into a nicer structure

    def action_back(self) -> None:
        self.app.pop_screen()


class StationSelectorScreen(Screen):
    BINDINGS = [("escape", "back", "Back")]
    stations_data = reactive([])

    def __init__(self, stations_data, station_name_column_width):
        super().__init__()
        self.stations_data = stations_data
        self.station_name_column_width = station_name_column_width
        self._search_label: Label | None = None

    def compose(self) -> ComposeResult:
        yield Label(
            "Select a station (arrow keys + Enter, type to search):",
            id="title",
        )

        self._search_label = Label("Search: ", id="search_label")
        yield self._search_label

        yield ListView(
            *[
                StationListItem(data, self.station_name_column_width)
                for data in self.stations_data
            ],
            id="station_list",
        )

    async def on_key(self, event: events.Key) -> None:
        search_buffer, filtered_data = handle_key_press(event.key)

        if search_buffer or filtered_data:
            list_view = self.query_one("#station_list", ListView)
            list_view.clear()
            list_view.extend(
                [
                    StationListItem(data, self.station_name_column_width)
                    for data in filtered_data
                ]
            )

            if self._search_label:
                self._search_label.update(f"Search: {search_buffer}")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        await self.app.push_screen(
            PlatformSelectorScreen(event.item.station_info)
        )

    def action_back(self) -> None:
        self.app.exit()


class StationSelectorApp(App):
    CSS_PATH = "layout.css"

    def __init__(self, stations_data, station_name_column_width):
        super().__init__()

        set_all_station_data(stations_data)
        set_filtered_station_data(stations_data)

        self.stations_data = stations_data
        self.station_name_column_width = station_name_column_width

    async def on_mount(self) -> None:
        await self.push_screen(
            StationSelectorScreen(
                self.stations_data,
                self.station_name_column_width,
            )
        )
