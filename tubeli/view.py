from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Container
from textual import events
from textual.reactive import reactive
from model import (
    handle_key_press,
    set_all_station_data,
    set_filtered_station_data,
)


class StationListItem(ListItem):
    """Custom ListItem for displaying station names."""

    def __init__(self, station_info):
        super().__init__()
        self.station_info = station_info

    def compose(self):
        lines = [
            Label(line['line_name']) for line in self.station_info['lines']
        ]
        yield Container(
            Label(self.station_info["commonName"]), *lines, id="list-item"
        )


class StationSelectorApp(App):
    """Textual app to interactively select a station with type-ahead search."""

    CSS_PATH = "layout.css"
    station_data = reactive([])

    def __init__(self, station_data):
        super().__init__()

        self._search_label = None
        set_all_station_data(station_data)
        set_filtered_station_data(station_data)
        self.station_data = station_data

    def compose(self) -> ComposeResult:
        """Create the UI layout."""

        yield Label(
            "Select a station (arrow keys + Enter, type to search):", id="title"
        )
        self._search_label = Label("Search: ", id="search_label")
        yield self._search_label
        yield ListView(
            *[StationListItem(data) for data in self.station_data],
            id="station_list",
        )

    async def on_key(self, event: events.Key) -> None:
        """Handle search typing and key presses."""

        search_buffer, filtered_data = handle_key_press(event.key)

        if search_buffer or filtered_data:
            list_view = self.query_one("#station_list", ListView)
            list_view.clear()
            list_view.extend([StationListItem(data) for data in filtered_data])

            self._search_label.update(f"Search: {search_buffer}")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection: print station name and exit."""

        self.exit(result=event.item.station_info)
