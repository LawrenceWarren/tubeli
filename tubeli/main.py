from model import (
    fetch_stop_points_by_mode,
    fetch_transport_interchanges,
    merge_stations,
    fetch_lines_arrivals,
    get_line_ids_names,
)
from view import StationSelectorApp
from json import dumps as json_dumps


def main():
    # Fetch datasets
    elizabeth = fetch_stop_points_by_mode('elizabeth-line', 'NaptanRailStation')
    overground = fetch_stop_points_by_mode('overground', 'NaptanRailStation')
    tube = fetch_stop_points_by_mode('tube', 'NaptanMetroStation')
    dlr = fetch_stop_points_by_mode('dlr', 'NaptanMetroStation')

    line_ids_names = get_line_ids_names()

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

    station_name_column_width = (
        max(len(station["commonName"]) for station in merged_stations) + 1
    )

    app = StationSelectorApp(merged_stations, line_ids_names)
    result = app.run()
    merged = {}

    if result:
        for mode in result["modes"]:
            merged |= fetch_lines_arrivals(result["modes"][mode])

    print(json_dumps(merged, indent=2))
    return


if __name__ == "__main__":
    main()
