
import os
import time
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import psycopg
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from database_config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)

# =========================================================
# CONFIGURATION
# =========================================================

STATION_IDS = [
    24415, 24416, 24418, 24420,
    24421, 24422, 24423, 24424
]

TIMEZONE = ZoneInfo("America/New_York")

# Historical collection start date
FROM_DATE = "2026-03-01"
TO_DATE = None

TEST_MODE = False
TEST_STATION_ID = 24415
TEST_DATE = "2026-10-01"

API_LIMIT = 100
MIN_INTERVAL_SECONDS = 1
REQUEST_DELAY = 0.2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("historical_ingestion")


# =========================================================
# HTTP SESSION WITH RETRIES
# =========================================================

def create_session():
    session = requests.Session()

    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# =========================================================
# SAVE DETECTION
# =========================================================

def save_detection(conn, detection, fallback_station_id):
    species_data = detection.get("species") or {}
    soundscape_data = detection.get("soundscape") or {}

    timestamp_value = detection.get("timestamp")

    if not timestamp_value:
        raise ValueError(
            f"Missing timestamp for detection {detection.get('id')}"
        )

    detection_dt = datetime.fromisoformat(
        timestamp_value.replace("Z", "+00:00")
    )

    if detection_dt.tzinfo is None:
        raise ValueError(
            f"Timezone missing for detection {detection.get('id')}"
        )

    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO detections (
                id,
                station_id,
                timestamp,
                confidence,
                probability,
                score,
                certainty,
                lat,
                lon,
                species,
                scientific_name,
                png_url,
                soundscape_url
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT DO NOTHING
            """,
            (
                detection.get("id"),
                detection.get("stationId") or fallback_station_id,
                detection_dt,
                detection.get("confidence"),
                detection.get("probability"),
                detection.get("score"),
                detection.get("certainty"),
                detection.get("lat"),
                detection.get("lon"),
                species_data.get("commonName") or "Unknown",
                species_data.get("scientificName"),
                species_data.get("pngUrl"),
                soundscape_data.get("url"),
            ),
        )

        return cursor.rowcount > 0


# =========================================================
# FETCH DETECTIONS WITH AUTOMATIC INTERVAL SPLITTING
# =========================================================

def fetch_detections_for_interval(
    session,
    url,
    start_dt,
    end_dt,
):
    """
    Fetch detections within an interval.

    If the API returns its full 100-record limit,
    divide the interval into two smaller intervals.

    Uses UTC timestamps to avoid daylight-saving
    ambiguities during API requests.
    """

    if start_dt >= end_dt:
        return []

    params = {
        "limit": API_LIMIT,
        "from": start_dt.astimezone(timezone.utc).isoformat(),
        "to": end_dt.astimezone(timezone.utc).isoformat(),
        "order": "asc",
    }

    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("success") is False:
        raise RuntimeError(
            f"BirdWeather API reported failure: {url}"
        )

    detections = data.get("detections")

    if not isinstance(detections, list):
        raise ValueError(
            "BirdWeather response has no valid detections list"
        )

    if len(detections) < API_LIMIT:
        time.sleep(REQUEST_DELAY)
        return detections

    duration_seconds = (
        end_dt - start_dt
    ).total_seconds()

    if duration_seconds <= MIN_INTERVAL_SECONDS:
        raise RuntimeError(
            "API limit still reached at minimum interval: "
            f"{start_dt} to {end_dt}. "
            "This interval needs manual review."
        )

    midpoint = start_dt + (end_dt - start_dt) / 2

    logger.info(
        "Splitting busy interval: %s to %s",
        start_dt,
        end_dt,
    )

    first_half = fetch_detections_for_interval(
        session,
        url,
        start_dt,
        midpoint,
    )

    second_half = fetch_detections_for_interval(
        session,
        url,
        midpoint,
        end_dt,
    )

    # Remove duplicate IDs returned at interval boundaries
    unique = {}

    for detection in first_half + second_half:
        detection_id = detection.get("id")

        if detection_id is None:
            raise ValueError(
                "Detection returned without an ID"
            )

        unique[detection_id] = detection

    return list(unique.values())


# =========================================================
# PROCESS A SINGLE STATION AND TIME INTERVAL
# =========================================================

def process_interval(
    conn,
    session,
    station_id,
    start_dt,
    end_dt,
):
    url = (
        "https://app.birdweather.com/api/v1/"
        f"stations/{station_id}/detections"
    )

    detections = fetch_detections_for_interval(
        session,
        url,
        start_dt,
        end_dt,
    )

    inserted_count = 0

    try:
        for detection in detections:
            if save_detection(
                conn,
                detection,
                station_id,
            ):
                inserted_count += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    logger.info(
        "Station %s | %s to %s | fetched=%s | inserted=%s",
        station_id,
        start_dt.isoformat(),
        end_dt.isoformat(),
        len(detections),
        inserted_count,
    )

    return len(detections), inserted_count


# =========================================================
# DATE RANGE CONFIGURATION
# =========================================================

def get_date_range():
    if TEST_MODE:
        test_date = datetime.strptime(
            TEST_DATE,
            "%Y-%m-%d",
        ).date()

        return test_date, test_date + timedelta(days=1)

    start_date = datetime.strptime(
        FROM_DATE,
        "%Y-%m-%d",
    ).date()

    if TO_DATE:
        end_date = datetime.strptime(
            TO_DATE,
            "%Y-%m-%d",
        ).date() + timedelta(days=1)
    else:
        end_date = (
            datetime.now(TIMEZONE).date()
            + timedelta(days=1)
        )

    if end_date <= start_date:
        raise ValueError("Invalid historical date range")

    return start_date, end_date


# =========================================================
# MAIN HISTORICAL INGESTION
# =========================================================

def pull_historic_data():
    start_date, end_date = get_date_range()

    stations = (
        [TEST_STATION_ID]
        if TEST_MODE
        else STATION_IDS
    )

    logger.info(
        "Historical ingestion started | test_mode=%s",
        TEST_MODE,
    )

    logger.info(
        "Stations: %s | Dates: %s through %s (exclusive)",
        stations,
        start_date,
        end_date,
    )

    total_fetched = 0
    total_inserted = 0
    failed_intervals = []

    with create_session() as session:
        with psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:

            for station_id in stations:
                logger.info(
                    "Processing station %s",
                    station_id,
                )

                current_date = start_date

                while current_date < end_date:
                    next_date = current_date + timedelta(days=1)

                    # Local midnight boundaries are converted
                    # to UTC before hourly iteration.
                    # This handles 23/25-hour DST days.
                    day_start = datetime.combine(
                        current_date,
                        datetime.min.time(),
                        tzinfo=TIMEZONE,
                    ).astimezone(timezone.utc)

                    day_end = datetime.combine(
                        next_date,
                        datetime.min.time(),
                        tzinfo=TIMEZONE,
                    ).astimezone(timezone.utc)

                    current = day_start

                    while current < day_end:
                        next_hour = min(
                            current + timedelta(hours=1),
                            day_end,
                        )

                        try:
                            fetched, inserted = process_interval(
                                conn,
                                session,
                                station_id,
                                current,
                                next_hour,
                            )

                            total_fetched += fetched
                            total_inserted += inserted

                        except Exception as exc:
                            conn.rollback()

                            failed_intervals.append(
                                (
                                    station_id,
                                    current.isoformat(),
                                    next_hour.isoformat(),
                                    str(exc),
                                )
                            )

                            logger.error(
                                "Station %s failed for %s to %s: %s",
                                station_id,
                                current,
                                next_hour,
                                exc,
                            )

                        current = next_hour

                    current_date = next_date

    logger.info(
        "Historical ingestion finished | fetched=%s | inserted=%s",
        total_fetched,
        total_inserted,
    )

    if failed_intervals:
        logger.warning(
            "%s intervals failed and require retry:",
            len(failed_intervals),
        )

        for station_id, start, end, error in failed_intervals:
            logger.warning(
                "Station %s | %s to %s | %s",
                station_id,
                start,
                end,
                error,
            )

        raise RuntimeError(
            f"Historical ingestion incomplete: "
            f"{len(failed_intervals)} intervals failed"
        )

    logger.info(
        "All requested historical intervals processed successfully."
    )


if __name__ == "__main__":
    pull_historic_data()
