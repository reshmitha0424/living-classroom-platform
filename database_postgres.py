import psycopg

from db_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def init_db():
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id BIGINT PRIMARY KEY,
                station_id INTEGER,
                timestamp TIMESTAMPTZ,
                confidence DOUBLE PRECISION,
                probability DOUBLE PRECISION,
                score DOUBLE PRECISION,
                certainty TEXT,
                lat DOUBLE PRECISION,
                lon DOUBLE PRECISION,
                species TEXT,
                scientific_name TEXT,
                png_url TEXT,
                soundscape_url TEXT
            )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_detection
            ON detections (station_id, timestamp, species)
        """)

    conn.commit()
    conn.close()

    print("PostgreSQL detections table initialized successfully.")


if __name__ == "__main__":
    init_db()
