# =========================================================
# IMPORTS
# =========================================================

import requests          # Handles BirdWeather API requests
import psycopg           # PostgreSQL database operations
import time              # Controls polling intervals
from datetime import datetime, timezone

from database_config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)

# =========================================================
# BIRDWEATHER STATION CONFIGURATION
# =========================================================

# --------- Single station configuration ---------
# Active BirdWeather station IDs used for ingestion
STATION_IDS = [24415, 24416, 24418, 24420, 24421, 24422, 24423, 24424]

# =========================================================
# GET LATEST STORED TIMESTAMP
# =========================================================

# Retrieve latest detection timestamp for a station
# Used to avoid reprocessing older detections
def get_latest_timestamp(conn, station_id):

    with conn.cursor() as cursor:

        row = cursor.execute("""
            SELECT MAX(timestamp)
            FROM detections
            WHERE station_id = %s
        """, (station_id,)).fetchone()

        return row[0] if row and row[0] else None


# =========================================================
# SAVE DETECTION RECORD
# =========================================================

# Insert BirdWeather detection into database
def save_detection(conn, detection, fallback_station_id):
    with conn.cursor() as cursor:

        species_data = detection.get("species") or {}               # Extract nested species metadata
        soundscape_data = detection.get("soundscape") or {}         # Extract soundscape audio metadata

        # Insert detection record into PostgreSQL database
        cursor.execute("""
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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """, (
            # Detection metadata
            detection.get("id"),
            detection.get("stationId") or fallback_station_id,
            detection.get("timestamp"),

            # Detection confidence metrics
            detection.get("confidence"),
            detection.get("probability"),
            detection.get("score"),
            detection.get("certainty"),

            # Geospatial coordinates
            detection.get("lat"),
            detection.get("lon"),

            # Species information
            species_data.get("commonName") or "Unknown",
            species_data.get("scientificName"),

            # Species image URL
            species_data.get("pngUrl"),

            # Detection audio URL
            soundscape_data.get("url")
        ))

        # Check whether new record was inserted or ignored as duplicate
        if cursor.rowcount > 0:

            print(
                "Saved:",
                fallback_station_id,
                species_data.get("commonName"),
                detection.get("timestamp")
            )
            return True
        else:
            print("Duplicate ignored:", fallback_station_id, species_data.get("commonName"), detection.get("timestamp"))
            return False


# =========================================================
# SINGLE STATION INGESTION (INITIAL VERSION)
# =========================================================

# Earlier ingestion logic used for testing a single BirdWeather station
# This version continuously fetched detections from one PUC every 10 seconds

# while True:

#     try:

#         # Send API request to BirdWeather endpoint
#         r = requests.get(URL, timeout=20)

#         # Raise exception for failed API responses
#         r.raise_for_status()

#         # Convert API response into JSON format
#         data = r.json()

#         # Extract detection records from response
#         detections = data.get("detections", [])

#         for d in detections:

#             # Extract detection metadata
#             species = (d.get("species") or {}).get("commonName") or "Unknown"
#             ts = d.get("timestamp")
#             conf = d.get("confidence")
#             lat = d.get("lat")
#             lon = d.get("lon")

#             # Store detection in database
#             save_detection(species, ts, conf, lat, lon)

#     # Handle API or ingestion failures safely
#     except Exception as e:

#         print("Error:", e)

#     # Wait before next polling cycle
#     time.sleep(10)


# =========================================================
# MULTI-STATION REAL-TIME INGESTION LOOP
# =========================================================

# Continuously fetch detections from all configured BirdWeather stations
while True:

    # Establish database connection for the current polling cycle
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    except psycopg.OperationalError as e:
        print("PostgreSQL unavailable; retrying in 10 seconds:", e)
        time.sleep(10)
        continue

    try:

        # Loop through each configured station
        for station_id in STATION_IDS:

            # Build station-specific BirdWeather API URL
            url = f"https://app.birdweather.com/api/v1/stations/{station_id}/detections"

            # Request latest detections from BirdWeather API
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()                                                                  
            
            detections = data.get("detections", [])             # Extract detection records from API response            
            latest_ts = get_latest_timestamp(conn, station_id)  # Get latest stored timestamp for this station
            new_count = 0                                       # Track number of new detections inserted

            # Process each detection returned by the API
            for d in detections:
                detection_ts = d.get("timestamp")
                detection_dt = datetime.fromisoformat(detection_ts.replace("Z", "+00:00"))
                if detection_dt.tzinfo is None:
                    detection_dt = detection_dt.replace(tzinfo=timezone.utc)

                # Skip detections already stored in the database
                if latest_ts and detection_dt <= latest_ts:
                    continue

                # Save new detection record
                if save_detection(conn, d, station_id):
                    new_count += 1

            # Commit saved detections for the current station
            conn.commit()
            print(f"Station {station_id}: {new_count} new detections saved")

    # Handle API, database, or ingestion errors safely
    except Exception as e:
        print("Error:", e)
    
    conn.close()                                                # Close database connection after each polling cycle  
    time.sleep(60)                                              # Wait before checking for new detections again
