import requests
import psycopg
import time
from datetime import datetime, timedelta, timezone

from db_config import (
    BIRDWEATHER_AUTH_KEY,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)

STATION_ID = 14218

FROM_DATE = "2025-11-15"
TO_DATE = "2026-07-29"


def save_detection(conn, detection):
    species_data = detection.get("species") or {}
    soundscape_data = detection.get("soundscape") or {}
    timestamp_value = detection.get("timestamp")
    detection_dt = datetime.fromisoformat(
        timestamp_value.replace("Z", "+00:00")
    )

    if detection_dt.tzinfo is None:
        detection_dt = detection_dt.replace(tzinfo=timezone.utc)

    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO detections (
                id, station_id, timestamp, confidence, probability, score,
                certainty, lat, lon, species, scientific_name, png_url, soundscape_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            detection.get("id"),
            detection.get("stationId") or STATION_ID,
            detection_dt,
            detection.get("confidence"),
            detection.get("probability"),
            detection.get("score"),
            detection.get("certainty"),
            detection.get("lat"),
            detection.get("lon"),
            species_data.get("commonName"),
            species_data.get("scientificName"),
            species_data.get("pngUrl"),
            soundscape_data.get("url")
        ))


def pull_historic_data():
    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:
        url = f"https://app.birdweather.com/api/v1/stations/{BIRDWEATHER_AUTH_KEY}/detections"

        start_dt = datetime.fromisoformat(FROM_DATE)
        end_dt = datetime.fromisoformat(TO_DATE) + timedelta(days=1)

        total_fetched = 0
        warning_hours = []
        range_start = start_dt

        while range_start < end_dt:
            range_end = min(
                range_start + timedelta(days=1),
                end_dt
            )

            print(f"\nProcessing date: {range_start.date()}")

            current = range_end - timedelta(hours=1)

            while current >= range_start:
                next_hour = current + timedelta(hours=1)

                from_time = current.isoformat()
                to_time = next_hour.isoformat()

                print(f"\nFetching hour: {from_time} to {to_time}")

                params = {
                    "limit": 100,
                    "from": from_time,
                    "to": to_time,
                    "order": "asc"
                }

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                detections = data.get("detections", [])

                for detection in detections:
                    save_detection(conn, detection)

                conn.commit()

                total_fetched += len(detections)

                print(f"Fetched {len(detections)} detections")
                print(f"Total fetched so far: {total_fetched}")

                if len(detections) == 100:
                    warning_hours.append((from_time, to_time))
                    print(f"WARNING HOUR SAVED: {from_time} to {to_time}")

                current -= timedelta(hours=1)
                time.sleep(0.2)

            range_start = range_end

        print("\nWARNING HOURS THAT NEED 15-MIN FETCH:")
        if warning_hours:
            for start, end in warning_hours:
                print(start, "to", end)
        else:
            print("No warning hours found.")

    print("\nDone. Historical data successfully loaded into the PostgreSQL database.")


if __name__ == "__main__":
    pull_historic_data()
