# gpx2fit

A command-line tool to convert GPX files to Garmin FIT format.

Preserves GPS coordinates, elevation, timestamps, heart rate, cadence, and speed data. The resulting FIT files are compatible with Garmin Connect, Strava, [SweatDiary](https://sweatdiary.app/) and other platforms that accept the FIT format.

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/cwern1/gpx2fit.git
cd gpx2fit
uv sync
```

## Usage

### Convert a single GPX file

```bash
uv run gpx2fit convert morning_run.gpx --sport running
```

This creates `morning_run.fit` in the same directory.

```
gpx2fit convert [-h] -s SPORT [-o OUTPUT] gpx_file
```

| Option | Description |
|---|---|
| `gpx_file` | Path to the input GPX file |
| `-s`, `--sport` | Sport type (required) — see [supported sports](#supported-sport-types) |
| `-o`, `--output` | Output file path (default: input filename with `.fit` extension) |

### Split a multi-track GPX file

If your GPX file contains multiple activities (tracks), you can split them into individual FIT files in one go:

```bash
uv run gpx2fit split export.gpx -o activities/
```

This creates one FIT file per track, named `YYYY-MM-DD--sport-type.fit`. The sport type is auto-detected from the track name (supports German activity names from rubiTrack / Apple Watch exports like *Laufen*, *Radfahren*, *Wandern*). Tracks without a recognized sport type are skipped.

```
gpx2fit split [-h] [-o OUTPUT_DIR] gpx_file
```

| Option | Description |
|---|---|
| `gpx_file` | Path to the multi-track GPX file |
| `-o`, `--output-dir` | Output directory (default: `output/`) |

### Examples

```bash
# Single file conversion
uv run gpx2fit convert ride.gpx -s cycling
uv run gpx2fit convert trail.gpx -s hiking -o activities/trail.fit
uv run gpx2fit convert session.gpx -s surfing

# Batch split
uv run gpx2fit split my_export.gpx
uv run gpx2fit split my_export.gpx -o fit_files/
```

## Supported GPX Data

The converter reads standard GPX 1.1 trackpoint data and common extensions:

| Field | GPX Source |
|---|---|
| Latitude / Longitude | `<trkpt lat="..." lon="...">` |
| Elevation | `<ele>` |
| Timestamp | `<time>` |
| Heart rate | `<gpxdata:hr>` extension |
| Cadence | `<gpxdata:cadence>` extension |

Speed and distance are computed automatically from GPS coordinates and timestamps.

## Dependencies

- [fit-tool](https://pypi.org/project/fit-tool/) — FIT file encoding (BSD-3-Clause)
- [gpxpy](https://pypi.org/project/gpxpy/) — GPX file parsing (Apache 2.0)
- [geopy](https://pypi.org/project/geopy/) — geodesic distance calculations (MIT)

All dependencies are installed automatically via `uv sync`.

## Supported Sport Types

All sport types from the Garmin FIT protocol are supported:

`alpine_skiing`, `american_football`, `basketball`, `boating`, `boxing`, `cross_country_skiing`, `cycling`, `diving`, `driving`, `e_biking`, `fishing`, `fitness_equipment`, `floor_climbing`, `flying`, `golf`, `hang_gliding`, `hiking`, `horseback_riding`, `hunting`, `ice_skating`, `inline_skating`, `jumpmaster`, `kayaking`, `kitesurfing`, `motorcycling`, `mountaineering`, `multisport`, `paddling`, `rafting`, `rock_climbing`, `rowing`, `running`, `sailing`, `sky_diving`, `snowboarding`, `snowmobiling`, `snowshoeing`, `soccer`, `stand_up_paddleboarding`, `surfing`, `swimming`, `tactical`, `tennis`, `training`, `transition`, `wakeboarding`, `walking`, `water_skiing`, `windsurfing`

