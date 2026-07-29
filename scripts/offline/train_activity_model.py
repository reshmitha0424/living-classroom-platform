import sqlite3
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


DB_NAME = "birds_v2.db"


def train_activity_model():
    # Connect to database
    conn = sqlite3.connect(DB_NAME)

    # Pull timestamps from detections table
    query = """
        SELECT timestamp
        FROM detections
        WHERE timestamp IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Convert timestamp safely because DB has mixed timezone formats
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )

    df = df.dropna(subset=["timestamp"])

    # Round each detection down to the hour
    df["hour_bucket"] = df["timestamp"].dt.floor("h")

    # Count detections per hour
    hourly = (
        df.groupby("hour_bucket")
        .size()
        .reset_index(name="detection_count")
        .sort_values("hour_bucket")
    )

    # Time-based features
    hourly["hour"] = hourly["hour_bucket"].dt.hour
    hourly["day_of_week"] = hourly["hour_bucket"].dt.dayofweek
    hourly["month"] = hourly["hour_bucket"].dt.month

    # Previous activity features
    hourly["prev_hour_count"] = hourly["detection_count"].shift(1)
    hourly["prev_3hr_avg"] = hourly["detection_count"].shift(1).rolling(3).mean()

    hourly = hourly.dropna()

    # Define 3 activity levels based on hourly detection count
    # 0 = Low Activity
    # 1 = Normal Activity
    # 2 = High Activity

    def label_activity(count):
        if count <= 30:
            return 0
        elif count <= 80:
            return 1
        else:
            return 2

    hourly["activity_level"] = hourly["detection_count"].apply(label_activity)

    print("Activity levels:")
    print("0 = Low Activity: 0–30 detections/hour")
    print("1 = Normal Activity: 31–80 detections/hour")
    print("2 = High Activity: 81+ detections/hour")
    print("Total hourly records:", len(hourly))

    # Features and target
    X = hourly[
        [
            "hour",
            "day_of_week",
            "month",
            "prev_hour_count",
            "prev_3hr_avg"
        ]
    ]

    y = hourly["activity_level"]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    # Model
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    print("\nMODEL RESULTS")
    print("Accuracy:", accuracy_score(y_test, y_pred))

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print("\nFeature Importance:")
    for feature, importance in zip(X.columns, model.feature_importances_):
        print(feature, ":", round(importance, 3))


if __name__ == "__main__":
    train_activity_model()