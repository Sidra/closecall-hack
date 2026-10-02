#!/usr/bin/env bash
# Download the four CC BY-SA 4.0 intersection clips from Wikimedia Commons into data/raw/.
set -euo pipefail
cd "$(dirname "$0")/../data" && mkdir -p raw && cd raw
UA="closecall/0.1 (research; contact via repo)"
get() { [ -s "$1" ] || curl -sfL -A "$UA" -o "$1" "$2"; }
get pieix.webm       "https://upload.wikimedia.org/wikipedia/commons/1/18/Intersection_Pie-IX-Sherbrooke.webm"
get tyumen-prof.webm "https://upload.wikimedia.org/wikipedia/commons/1/14/Kruci%C4%9Do_de_stratoj_Respubliko_kaj_Profsojuznaja_%28Tjumeno%29.webm"
get tyumen-vodo.webm "https://upload.wikimedia.org/wikipedia/commons/d/d6/Kruci%C4%9Do_de_stratoj_Respubliko_kaj_Vodoprovodnaja_%28Tjumeno%29.webm"
get chiangmai.ogv    "https://upload.wikimedia.org/wikipedia/commons/2/21/A_intersection_with_traffic_in_Chiang_Mai%2C_Thailand.ogv"
ls -la
