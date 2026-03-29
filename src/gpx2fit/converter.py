from pathlib import Path

import gpxpy
from geopy.distance import geodesic

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import (
    Event,
    EventType,
    FileType,
    Manufacturer,
    Sport,
    SubSport,
)

_EXCLUDED_SPORTS = {"GENERIC", "ALL"}

SPORT_MAP = {
    s.name.lower(): (s, SubSport.GENERIC)
    for s in Sport
    if s.name not in _EXCLUDED_SPORTS
}

SPORT_NAMES = sorted(SPORT_MAP.keys())

# German activity names from rubiTrack / Apple Watch exports
GERMAN_SPORT_MAP = {
    "laufen": "running",
    "radfahren": "cycling",
    "wandern": "hiking",
    "langlaufen": "cross_country_skiing",
    "mountainbiken": "cycling",
    "schwimmen": "swimming",
    "gehen": "walking",
}


def _parse_extensions(trkpt):
    """Extract heart rate and cadence from GPX trackpoint extensions."""
    hr = 0
    cadence = 0
    for ext in trkpt.extensions:
        for child in list(ext) or [ext]:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "hr":
                hr = int(float(child.text))
            elif tag == "cadence":
                cadence = int(float(child.text))
    return hr, cadence


def _timestamp_ms(dt):
    """Convert datetime to milliseconds since Unix epoch."""
    return round(dt.timestamp() * 1000)


def _detect_sport(track_name: str) -> str | None:
    """Extract sport name from a GPX track name like 'Aachen ---- Radfahren'."""
    if not track_name:
        return None
    parts = track_name.split("----")
    if len(parts) >= 2:
        german = parts[-1].strip().lower()
        return GERMAN_SPORT_MAP.get(german)
    return None


def convert_gpx_to_fit(gpx_path: Path, fit_path: Path, sport_name: str):
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            points.extend(segment.points)

    if not points:
        raise ValueError(f"No trackpoints found in {gpx_path}")

    _write_fit(points, fit_path, sport_name)


def split_gpx_to_fit(gpx_path: Path, output_dir: Path):
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)

    output_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    for track in gpx.tracks:
        sport_name = _detect_sport(track.name)
        if sport_name is None:
            skipped += 1
            continue

        points = []
        for segment in track.segments:
            points.extend(segment.points)
        if not points:
            skipped += 1
            continue

        dt = points[0].time
        filename = f"{dt.strftime('%Y-%m-%d')}--{sport_name}.fit"

        # Handle duplicate filenames by appending a counter
        fit_path = output_dir / filename
        counter = 2
        while fit_path.exists():
            stem = f"{dt.strftime('%Y-%m-%d')}--{sport_name}-{counter}"
            fit_path = output_dir / f"{stem}.fit"
            counter += 1

        _write_fit(points, fit_path, sport_name)
        converted += 1

    return converted, skipped


def _write_fit(points: list, fit_path: Path, sport_name: str):
    sport, sub_sport = SPORT_MAP[sport_name]

    start_time = _timestamp_ms(points[0].time)
    end_time = _timestamp_ms(points[-1].time)

    # File ID
    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.serial_number = 0x12345678
    file_id.time_created = start_time

    # Start event
    event_start = EventMessage()
    event_start.event = Event.TIMER
    event_start.event_type = EventType.START
    event_start.timestamp = start_time

    # Build records
    records = []
    cumulative_distance = 0.0
    hr_values = []
    cadence_values = []
    speed_values = []
    total_ascent = 0.0
    total_descent = 0.0
    prev_elevation = None

    for i, pt in enumerate(points):
        segment_distance = 0.0
        if i > 0:
            prev = points[i - 1]
            segment_distance = geodesic(
                (prev.latitude, prev.longitude),
                (pt.latitude, pt.longitude),
            ).meters
            cumulative_distance += segment_distance

        hr, cadence = _parse_extensions(pt)

        rec = RecordMessage()
        rec.timestamp = _timestamp_ms(pt.time)
        rec.position_lat = pt.latitude
        rec.position_long = pt.longitude
        rec.distance = cumulative_distance

        # Speed (m/s) from distance/time delta
        if i > 0:
            dt = (pt.time - points[i - 1].time).total_seconds()
            if dt > 0:
                speed = segment_distance / dt
                rec.enhanced_speed = speed
                speed_values.append(speed)

        if pt.elevation is not None:
            rec.altitude = pt.elevation
            if prev_elevation is not None:
                diff = pt.elevation - prev_elevation
                if diff > 0:
                    total_ascent += diff
                else:
                    total_descent += abs(diff)
            prev_elevation = pt.elevation

        if hr > 0:
            rec.heart_rate = hr
            hr_values.append(hr)
        if cadence > 0:
            rec.cadence = cadence
            cadence_values.append(cadence)

        records.append(rec)

    # Stop event
    event_stop = EventMessage()
    event_stop.event = Event.TIMER
    event_stop.event_type = EventType.STOP_ALL
    event_stop.timestamp = end_time

    elapsed_time_s = (end_time - start_time) / 1000.0

    # Lap
    lap = LapMessage()
    lap.timestamp = end_time
    lap.start_time = start_time
    lap.total_elapsed_time = elapsed_time_s
    lap.total_timer_time = elapsed_time_s
    lap.total_distance = cumulative_distance
    lap.start_position_lat = points[0].latitude
    lap.start_position_long = points[0].longitude
    lap.end_position_lat = points[-1].latitude
    lap.end_position_long = points[-1].longitude
    lap.sport = sport
    lap.event = Event.LAP
    lap.event_type = EventType.STOP
    lap.total_ascent = round(total_ascent)
    lap.total_descent = round(total_descent)
    if hr_values:
        lap.avg_heart_rate = round(sum(hr_values) / len(hr_values))
        lap.max_heart_rate = max(hr_values)
    if cadence_values:
        lap.avg_cadence = round(sum(cadence_values) / len(cadence_values))
        lap.max_cadence = max(cadence_values)
    if speed_values:
        lap.enhanced_avg_speed = sum(speed_values) / len(speed_values)
        lap.enhanced_max_speed = max(speed_values)

    # Session
    session = SessionMessage()
    session.timestamp = end_time
    session.start_time = start_time
    session.total_elapsed_time = elapsed_time_s
    session.total_timer_time = elapsed_time_s
    session.total_distance = cumulative_distance
    session.start_position_lat = points[0].latitude
    session.start_position_long = points[0].longitude
    session.sport = sport
    session.sub_sport = sub_sport
    session.first_lap_index = 0
    session.num_laps = 1
    session.total_ascent = round(total_ascent)
    session.total_descent = round(total_descent)
    session.event = Event.LAP
    session.event_type = EventType.STOP
    if speed_values:
        session.enhanced_avg_speed = sum(speed_values) / len(speed_values)
        session.enhanced_max_speed = max(speed_values)
    if hr_values:
        session.avg_heart_rate = round(sum(hr_values) / len(hr_values))
        session.max_heart_rate = max(hr_values)
    if cadence_values:
        session.avg_cadence = round(sum(cadence_values) / len(cadence_values))
        session.max_cadence = max(cadence_values)

    # Activity
    activity = ActivityMessage()
    activity.timestamp = end_time
    activity.total_timer_time = elapsed_time_s
    activity.num_sessions = 1
    activity.event = Event.ACTIVITY
    activity.event_type = EventType.STOP

    # Build FIT file
    builder = FitFileBuilder(auto_define=True, min_string_size=50)
    builder.add(file_id)
    builder.add(event_start)
    builder.add_all(records)
    builder.add(event_stop)
    builder.add(lap)
    builder.add(session)
    builder.add(activity)

    fit_file = builder.build()
    fit_file.to_file(str(fit_path))
