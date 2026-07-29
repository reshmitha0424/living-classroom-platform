import sqlite3
import pandas as pd

DB_NAME = "birds_v2.db"


def get_best_birdwatching_hours():
    conn = sqlite3.connect(DB_NAME)
    # Pull required columns from detections table
    query = """
        SELECT
            station_id,
            timestamp,
            species
        FROM detections
        WHERE timestamp IS NOT NULL
    """
    # Load SQL query result into pandas dataframe
    df = pd.read_sql_query(query, conn)
    conn.close() # Close DB connection

    # Convert timestamp to datetime format
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    # Extract hour
    df["hour"] = df["timestamp"].dt.hour

    # Overall best hours
    overall_hourly = (
        df.groupby("hour")
        .size()
        .reset_index(name="detection_count")
        .sort_values("detection_count", ascending=False)
    )

    print("\nOVERALL BEST BIRDWATCHING HOURS")
    print(overall_hourly.head(5))

    # Station-wise best hours
    station_hourly = (
        df.groupby(["station_id", "hour"])
        .size()
        .reset_index(name="detection_count")
    )

    best_by_station = (
        station_hourly.sort_values(["station_id", "detection_count"], ascending=[True, False])
        .groupby("station_id")
        .head(3)
    )

    print("\nBEST HOURS BY STATION")
    print(best_by_station)

    # Save results
    overall_hourly.to_csv("overall_best_birdwatching_hours.csv", index=False)
    best_by_station.to_csv("station_best_birdwatching_hours.csv", index=False)

    print("\nSaved:")
    print("overall_best_birdwatching_hours.csv")
    print("station_best_birdwatching_hours.csv")


if __name__ == "__main__":
    get_best_birdwatching_hours()