tidemark

Earth system trend analysis using NASA satellite data.

Runs Mann-Kendall trend detection on climate variables at any location,
projects when a not-yet-significant trend will cross the significance
threshold, and estimates when it hits real-world impact thresholds.

Data sources: NASA POWER, NASA GPM IMERG, NASA AppEEARS (MODIS), ORNL DAAC.

## usage

    tidemark analyze --location dhaka --var temperature
    tidemark analyze --location cairo --var rainfall
    tidemark analyze --lat 23.8 --lon 90.4 --var lst
    tidemark compare --location dhaka --location cairo --var rainfall

## install

    cargo build --release
    pip install -r python/requirements.txt

Requires Python 3 with pymannkendall, numpy, scipy, requests.
NASA GPM and AppEEARS variables require a free NASA Earthdata account.
Set EARTHDATA_TOKEN in a .env file at the project root.
