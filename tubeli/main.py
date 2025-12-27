from model import (
    fetch_stop_points,
    fetch_transport_interchanges,
    merge_stations,
    fetch_arrivals,
    TUBE_LINE_IDS,
    OVERGROUND_LINE_IDS,
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
            ('elizabeth-line', elizabeth),
            ('overground', overground),
            ('tube', tube),
            ('dlr', dlr),
        ],
        hub_common_names,
    )

    print(json_dumps(merged_stations))

    # Longest station names are
    # "King's Cross & St Pancras International"
    # 'Heathrow Airport Terminal 4'
    # TODO: Kings cross is bugged and fails to return any times - this is a trend with all many stations on the circle line
    # station_names = [s["commonName"] for s in merged_stations]
    # print(sorted(station_names, key=len, reverse=True))

    app = StationSelectorApp(merged_stations)
    result = app.run()

    if result:
        if "elizabeth-lineId" in result:
            print("elizabeth")
            print(
                json_dumps(
                    fetch_arrivals(result["elizabeth-lineId"], "elizabeth"),
                    indent=2,
                )
            )
        if "dlrId" in result:
            print("dlr")
            print(json_dumps(fetch_arrivals(result["dlrId"], "dlr"), indent=2))
        if "overgroundId" in result:
            for line in result["lines"]:
                if line["line_id"] in OVERGROUND_LINE_IDS:
                    print(f"{line["line_name"]}")
                    print(
                        json_dumps(
                            fetch_arrivals(
                                result["overgroundId"], line["line_id"]
                            ),
                            indent=2,
                        )
                    )
        if "tubeId" in result:
            for line in result["lines"]:
                if line["line_id"] in TUBE_LINE_IDS:
                    print(f"{line["line_name"]}")
                    print(
                        json_dumps(
                            fetch_arrivals(result["tubeId"], line["line_id"]),
                            indent=2,
                        )
                    )

    print(json_dumps(result, indent=2))
    return


if __name__ == "__main__":
    main()
