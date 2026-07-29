import pandas as pd
import sqlite3

DB_NAME = "birds_v2.db"
CSV_FILE = "combined_birdweather_data.csv"

COLUMN_MAPPING = {
    "id": "id",
    "stationId": "station_id",
    "timestamp": "timestamp",
    "confidence": "confidence",
    "probability": "probability",
    "score": "score",
    "certainty": "certainty",
    "lat": "lat",
    "lon": "lon",
    "species.commonName": "species",
    "species.scientificName": "scientific_name",
    "species.pngUrl": "png_url",
    "soundscape.url": "soundscape_url"
}

print("Reading CSV...")
df = pd.read_csv(CSV_FILE)

print("Keeping required columns...")
df = df[list(COLUMN_MAPPING.keys())]

print("Renaming columns...")
df.rename(columns=COLUMN_MAPPING, inplace=True)

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("Inserting data into database...")

for _, row in df.iterrows():
    cursor.execute("""
        INSERT OR IGNORE INTO detections (
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["id"],
        row["station_id"],
        row["timestamp"],
        row["confidence"],
        row["probability"],
        row["score"],
        row["certainty"],
        row["lat"],
        row["lon"],
        row["species"],
        row["scientific_name"],
        row["png_url"],
        row["soundscape_url"]
    ))

conn.commit()
conn.close()

print("Done. CSV data imported into birds_v2.db")