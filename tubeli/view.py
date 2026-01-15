from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label, Pretty, Static
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual import events
from textual.reactive import reactive
from datetime import datetime, timezone

from model import (
    handle_key_press,
    set_all_station_data,
    set_filtered_station_data,
    get_line_details_by_id,
    fetch_station_arrivals,
)

DIRECTION_ORDER = {
    "westbound": 0,
    "northbound": 0,
    "inbound": 0,
    "eastbound": 1,
    "southbound": 1,
    "outbound": 1,
}


class ArrivalRow(Static):
    def __init__(self, destination: str, expected_time: str):
        super().__init__()
        self.destination = destination
        self.expected_time = expected_time

    def on_mount(self):
        # self.styles.opacity = 0
        # self.animate("opacity", 1.0, duration=0.3)
        self.update_text()
        self.set_interval(15, self.update_text)

    def update_text(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        arrival_time = datetime.fromisoformat(
            self.expected_time.replace("Z", "+00:00")
        )

        delta = int((arrival_time - now).total_seconds())

        if delta <= 10:
            time_text = "Arrived"
        elif delta < 60:
            time_text = "1 min"
        else:
            mins = delta // 60
            time_text = f"{mins} min" if mins == 1 else f"{mins} mins"

        self.update(f"{time_text:<8} {self.destination}")


class ArrivalColumn(Vertical):
    def __init__(self, direction: str, arrivals: list[dict]):
        super().__init__()
        self.direction = direction
        self.arrivals = arrivals

    def compose(self):
        yield Static(self.direction.title(), classes="column_title")

        for arrival in self.arrivals:
            yield ArrivalRow(
                arrival["destination_name"],
                arrival["expected_time"],
            )


class LineBoard(Vertical):

    def __init__(
        self,
        line_id: str,
        line_name: str,
        arrivals_by_direction: dict[str, list[dict]],
    ):
        super().__init__()
        self.line_id = line_id
        self.line_name = line_name
        self.arrivals_by_direction = arrivals_by_direction

    def compose(self):
        info = get_line_details_by_id(self.line_id)
        line_label = Static(self.line_name, classes="line_title")
        line_label.styles.background = info["color"]
        line_label.styles.color = info["text_color"]
        line_label.styles.text_align = "center"
        yield line_label

        ordered_directions = sorted(
            self.arrivals_by_direction.items(),
            key=lambda item: DIRECTION_ORDER.get(item[0], 99),
        )

        yield Horizontal(
            *[
                ArrivalColumn(direction, arrivals)
                for direction, arrivals in ordered_directions
            ]
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


class ArrivalViewingScreen(Screen):
    BINDINGS = [("escape", "back", "Back")]
    merged_arrivals = reactive(dict)

    def __init__(self, station_info):
        super().__init__()
        self.station_info = station_info

    def compose(self) -> ComposeResult:
        yield Vertical(id="board")

    async def on_mount(self) -> None:
        self.refresh_arrivals()
        self.set_interval(15, self.refresh_arrivals)

    def refresh_arrivals(self) -> None:
        self.merged_arrivals = fetch_station_arrivals(self.station_info)

        board = self.query_one("#board", Vertical)

        # Batch DOM updates via the App
        with self.app.batch_update():
            board.remove_children()

            for line_id, line in sorted(
                self.merged_arrivals.items(),
                key=lambda item: item[1][
                    "line_name"
                ].lower(),  # sort by line_name
            ):
                board.mount(
                    LineBoard(
                        line_id,
                        line["line_name"],
                        line["arrivals"],
                    )
                )

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
            ArrivalViewingScreen(event.item.station_info)
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
