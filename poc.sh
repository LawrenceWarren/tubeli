#!/bin/bash

export CURRENT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "Current time: $CURRENT_TIME"

CHALK_FARM_ID=$(curl -s https://api.tfl.gov.uk/StopPoint/Search/chalkfarmunderground | jq -r '.matches[].id')
KENTISH_TOWN_WEST_ID=$(curl -s https://api.tfl.gov.uk/StopPoint/Search/kentishtownwestrailstation | jq -r '.matches[].id')

NL=$(curl -s https://api.tfl.gov.uk/StopPoint/${CHALK_FARM_ID}/Arrivals | jq '[.[] | select(.direction == "inbound") | {destination: (.towards | sub(" Rail Station"; "") | sub(" \\(London\\)"; "") | sub("via CX"; "via Charing X")), expectedArrival, timeToStation, line: .lineName}] | sort_by(.expectedArrival)[:3]')
ML=$(curl -s https://api.tfl.gov.uk/StopPoint/${KENTISH_TOWN_WEST_ID}/Arrivals | jq '[.[] | {destination: (.destinationName | sub(" Rail Station"; "") | sub(" \\(London\\)"; "")), expectedArrival, timeToStation, line: .lineName}] | sort_by(.expectedArrival)[:3]')

MERGED=$(jq -s '.[0] + .[1] | unique_by(.expectedArrival) | sort_by(.expectedArrival)' <(echo $ML) <(echo $NL))


echo $MERGED | jq


curl -s https://api.tfl.gov.uk/StopPoint/HUBBDS/Arrivals