from model import (
    fetch_stop_points_by_mode,
    fetch_transport_interchanges,
    merge_stations,
)
from view import StationSelectorApp
from json import dumps as json_dumps


def main():
    # Fetch datasets
    elizabeth = fetch_stop_points_by_mode('elizabeth-line', 'NaptanRailStation')
    overground = fetch_stop_points_by_mode('overground', 'NaptanRailStation')
    tube = fetch_stop_points_by_mode('tube', 'NaptanMetroStation')
    dlr = fetch_stop_points_by_mode('dlr', 'NaptanMetroStation')

    hub_common_names = fetch_transport_interchanges()

    merged_stations = merge_stations(
        [
            elizabeth,
            overground,
            tube,
            dlr,
        ],
        hub_common_names,
    )

    merged_stations.sort(key=lambda station: station["commonName"])

    station_name_column_width = (
        max(len(station["commonName"]) for station in merged_stations) + 3
    )

    app = StationSelectorApp(merged_stations, station_name_column_width)
    result = app.run()
    return


if __name__ == "__main__":
    main()
