from model import (
    fetch_stop_points,
    fetch_transport_interchanges,
    merge_stations,
    fetch_lines_arrivals,
)
from view import StationSelectorApp
from json import dumps as json_dumps


def main():
    # Fetch datasets
    elizabeth = fetch_stop_points('elizabeth-line', 'NaptanRailStation')
    overground = fetch_stop_points('overground', 'NaptanRailStation')
    tube = fetch_stop_points('tube', 'NaptanMetroStation')
    dlr = fetch_stop_points('dlr', 'NaptanMetroStation')

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

    # print(json_dumps(merged_stations))
    # return 0

    # Longest station names are
    # "King's Cross & St Pancras International"
    # 'Heathrow Airport Terminal 4'
    # TODO: Kings cross is bugged and fails to return any times - this is a trend with all many stations on the circle line
    # station_names = [s["commonName"] for s in merged_stations]
    # print(sorted(station_names, key=len, reverse=True))

    app = StationSelectorApp(merged_stations)
    result = app.run()
    merged = {}

    if result:
        for mode in result["modes"]:
            merged |= fetch_lines_arrivals(result["modes"][mode])

    print(json_dumps(merged, indent=2))
    return


if __name__ == "__main__":
    main()
