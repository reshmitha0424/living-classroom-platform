# =========================================================
# IMPORT REQUIRED LIBRARIES
# =========================================================
from flask import Flask, jsonify, render_template, request      # web application routing and API responses
from datetime import datetime, timedelta                        # handling timestamps and time-based filtering
from zoneinfo import ZoneInfo
import psycopg                                                  # PostgreSQL database connection library
import pandas as pd                                             # data processing and dataframe operations
from sklearn.ensemble import RandomForestClassifier             # machine learning predictions

from db_config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)


# =========================================================
# FLASK APPLICATION CONFIGURATION
# =========================================================
app = Flask(__name__)                                           # Initialize Flask application
LOCAL_TIMEZONE = ZoneInfo("America/New_York")


def get_db_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# =========================================================
# NON-BIRD SPECIES FILTER LIST
# =========================================================
# Detected species that are excluded from bird analytics
NON_BIRD_SPECIES = [
    "American Bullfrog",
    "American Toad",
    "Coyote",
    "Dog",
    "Eastern Gray Squirrel",
    "Engine",
    "Gray Treefrog",
    "Spring Peeper"
]


# =========================================================
# FILTER CONDITION BUILDER - TIME AND STATION FILTERS
# =========================================================
def get_filter_condition(filter_value, station_value):
    conditions = []                                             # SQL filter conditions
    params = []                                                 # corresponding query parameters


    # --- last 1 hour time filter --- #
    if filter_value == "1h":
        cutoff = (datetime.now().astimezone() - timedelta(hours=1)).isoformat()     # timestamp for one hour ago
        conditions.append("timestamp >= %s")                    # timestamp filter condition
        params.append(cutoff)                                   # Add timestamp value to query parameters


    # --- Today time filter --- #
    elif filter_value == "today":                               # Timestamp for Today - start of the day
        start_of_day = datetime.now().astimezone().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        conditions.append("timestamp >= %s")                    # timestamp filter condition
        params.append(start_of_day)                             # Add timestamp value to query parameters

    # --- Station specific filter --- #
    if station_value != "all":
        conditions.append("station_id = %s")                    # Filter records based on selected station
        params.append(station_value)                            # Add station ID to query parameters

    placeholders = ",".join(["%s"] * len(NON_BIRD_SPECIES))     # placeholders for excluded non-bird species
    conditions.append(f"species NOT IN ({placeholders})")       # Remove unwanted non-bird detections from results using placeholders
    params.extend(NON_BIRD_SPECIES)                             # Add excluded species values to query parameters

    return "WHERE " + " AND ".join(conditions), tuple(params)   # Returns Complete SQL query


# =========================================================
# MONITOR DASHBOARD (MAIN SCREEN)
# =========================================================
@app.get("/")
def monitor_dashboard():
    return render_template("monitor_dashboard.html")


# =========================================================
# INTERACTIVE DASHBOARD
# =========================================================
@app.get("/dashboard")
def dashboard():
    return render_template("index.html")


# =========================================================
# LATEST DETECTIONS
# =========================================================
# API endpoint for retrieving latest bird detections
@app.get("/latest")
def latest():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)            


        # Retrieve latest detection records from database
        rows = cursor.execute(f"""
            SELECT station_id, species, timestamp, confidence, png_url
            FROM detections
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT 5
        """, params).fetchall()

        # Close database connection after query execution
        conn.close()                                            

        # Store formatted API response data    
        result = []                                             

        # Convert database rows into JSON-friendly structure
        for r in rows:
            result.append({
                "station_id": r[0],
                "species": r[1],
                "timestamp": r[2].isoformat() if r[2] else None,
                "confidence": f"{r[3]:.3f}" if r[3] else "",
                "png_url": r[4]
            })

        # Return successful JSON response
        return jsonify(ok=True, rows=result)                    
    

    # Handle unexpected application errors safely
    except Exception as e:                                          
        return jsonify(ok=False, error=str(e))
    


# =========================================================
# SUMMARY
# =========================================================
# API endpoint for dashboard summary statistics
@app.get("/summary")
def summary():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()


        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)            


        # Total number of detections
        total_detections = cursor.execute(
            f"SELECT COUNT(*) FROM detections {where_clause}",
            params
        ).fetchone()[0]


        # Total number of unique bird species
        unique_species = cursor.execute(
            f"SELECT COUNT(DISTINCT species) FROM detections {where_clause}",
            params
        ).fetchone()[0]


        # # Retrieve most frequently detected species
        # top_species_row = cursor.execute(f"""
        #     SELECT species, COUNT(*) as cnt
        #     FROM detections
        #     {where_clause}
        #     GROUP BY species
        #     ORDER BY cnt DESC
        #     LIMIT 1
        # """, params).fetchone()


        # Retrieve latest detected species and timestamp
        latest_row = cursor.execute(f"""
            SELECT species, timestamp
            FROM detections
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT 1
        """, params).fetchone()

        # Close database connection after query execution
        conn.close()                                            


        # Return summary statistics as JSON response
        return jsonify(
            ok=True,
            total_detections=total_detections,
            unique_species=unique_species,
            # top_species=top_species_row[0] if top_species_row else "N/A",
            latest_species=latest_row[0] if latest_row else "N/A",
            latest_timestamp=(
                latest_row[1].isoformat()
                if latest_row and latest_row[1]
                else "N/A"
            )
        )


    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# =========================================================
# TOP SPECIES
# =========================================================
# API endpoint for retrieving most detected bird species
@app.get("/top-species")
def top_species():
    try:
        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)
                                                                
        # Retrieve top detected species with detection counts
        rows = cursor.execute(f"""
            SELECT 
                species,
                COUNT(*) as cnt,                                        
                MAX(png_url) as png_url
            FROM detections
            {where_clause}
            GROUP BY species
            ORDER BY cnt DESC
            LIMIT 5
        """, params).fetchall()

        # Close database connection after query execution   
        conn.close()                                                 

        # Return formatted JSON response
        return jsonify(ok=True, rows=[
            {
                "species": r[0],
                "count": r[1],
                "png_url": r[2]
            }
            for r in rows
        ])
    
    # Handle unexpected application errors 
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# =========================================================
# MONTHLY DETECTION TRENDS
# =========================================================
# API endpoint for retrieving monthly bird detection counts
@app.get("/monthly")
def monthly():
    try:
        # Establish database connection     
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)

        # Count detections grouped by month
        rows = cursor.execute(f"""
            SELECT 
                TO_CHAR(timestamp AT TIME ZONE 'America/New_York', 'MM') as month_num,
                COUNT(*) as cnt
            FROM detections
            {where_clause}
            GROUP BY month_num
            ORDER BY month_num
        """, params).fetchall()

        # Close database connection after query execution
        conn.close()

        # Map numeric month values to short month names
        month_names = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
            "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
            "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
        }

        # Initialize all months with zero detections
        counts = {m: 0 for m in month_names.keys()}

        # Update available months with actual detection counts
        for month_num, cnt in rows:
            if month_num in counts:
                counts[month_num] = cnt

        # Format monthly counts for frontend charts
        result = [
            {
                "month": month_names[m],
                "count": counts[m]
            }
            for m in month_names
        ]

        # Return monthly trend data as JSON response
        return jsonify(ok=True, rows=result)
    
    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))
    

# =========================================================
# LOCATIONS
# =========================================================
# API endpoint for retrieving map location data
@app.get("/locations")
def locations():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)


        # Exclude records without valid coordinates
        if where_clause:
            where_clause += " AND lat IS NOT NULL AND lon IS NOT NULL"
        else:
            where_clause = "WHERE lat IS NOT NULL AND lon IS NOT NULL"

        # Randomize map points for all-time overview; otherwise show latest detections first
        order_by = (
            "ORDER BY RANDOM()"
            if filter_value == "all" and station_value == "all"
            else "ORDER BY timestamp DESC"
        )

        # Retrieve detection locations for map visualization
        rows = cursor.execute(f"""
            SELECT station_id, species, lat, lon
            FROM detections
            {where_clause}
            {order_by}
            LIMIT 500
        """, params).fetchall()

        # Close database connection after query execution
        conn.close()

        # Return formatted map location data
        return jsonify([
            {
                "station_id": r[0],
                "species": r[1],
                "lat": r[2],
                "lon": r[3]
            }
            for r in rows
        ])

    # Return empty response if location query fails
    except Exception:
        return jsonify([])


# =========================================================
# SPECIES TIMELINE
# =========================================================
# API endpoint for retrieving species activity across monthly time buckets
@app.get("/species-timeline")
def species_timeline():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read dashboard filter selections from frontend
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)

        # Retrieve detection counts grouped by species and timestamp
        rows = cursor.execute(f"""
            SELECT species, timestamp, COUNT(*) as cnt
            FROM detections
            {where_clause}
            GROUP BY species, timestamp
        """, params).fetchall()


        # Close database connection after query execution
        conn.close()


        # Create four time buckets for each month
        buckets = []

        for month in range(1, 13):
            for part in range(1, 5):
                buckets.append(f"{month:02d}-{part}")

        # Store species-level timeline counts
        species_data = {}

        # Assign each detection count to the correct monthly bucket
        for species, ts, cnt in rows:
            try:

                # Extract month and day from timestamp
                local_ts = ts.astimezone(LOCAL_TIMEZONE)
                month = f"{local_ts.month:02d}"
                day = local_ts.day

                # Skip invalid month values 
                if month not in [f"{m:02d}" for m in range(1, 13)]:
                    continue


                # Divide each month into four approximate weekly parts            
                if day <= 7:
                    part = "1"
                elif day <= 15:
                    part = "2"
                elif day <= 23:
                    part = "3"
                else:
                    part = "4"


                # Create bucket key using month and part
                bucket = f"{month}-{part}"


                # Initialize bucket counts for new species
                if species not in species_data:
                    species_data[species] = {b: 0 for b in buckets}

                # Add detection count to the matching bucket
                species_data[species][bucket] += cnt

            # Skip malformed timestamps without stopping the endpoint
            except Exception:
                pass

        # Find highest bucket count for bar-height scaling        
        max_count = max(
            [count for s in species_data.values() for count in s.values()] or [1]
        )

        # Format species timeline data for frontend 
        result = []

        for species, counts in species_data.items():
            
            # Total detections for sorting
            total = sum(counts.values())
            values = []

            for b in buckets:
                # Convert bucket count into percentage height for timeline bars
                count = counts[b]
                percent = int((count / max_count) * 100) if count else 0
                values.append({
                    "count": count,
                    "percent": percent
                })

            result.append({
                "species": species,
                "total": total,
                "values": values
            })


        # Show only the top 10 species by total detections
        result = sorted(result, key=lambda x: x["total"], reverse=True)[:10]

        # Return timeline data as JSON response
        return jsonify(ok=True, rows=result)

    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))


# =========================================================
# SPECIES DETAIL
# =========================================================
# API endpoint for retrieving detailed information about a selected species
@app.get("/species-detail")
def species_detail():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read selected species and dashboard filters from frontend 
        species = request.args.get("species")
        filter_value = request.args.get("filter", "all")
        station_value = request.args.get("station", "all")

        # Generate SQL filter conditions dynamically
        where_clause, params = get_filter_condition(filter_value, station_value)


        # Add selected species condition to existing filters
        if where_clause:
            where_clause += " AND species = %s"
            params = params + (species,)
        else:
            where_clause = "WHERE species = %s"
            params = (species,)

        # Retrieve aggregated details for the selected species
        row = cursor.execute(f"""
            SELECT 
                species,
                COUNT(*) as total_detections,
                MIN(timestamp) as first_detected,
                MAX(timestamp) as last_detected,
                STRING_AGG(DISTINCT station_id::text, ',') as stations,
                MAX(CASE 
                    WHEN png_url LIKE 'https://media.birdweather.com%%' THEN png_url
                END) as png_url,
                MAX(soundscape_url) as soundscape_url,
                MAX(scientific_name) as scientific_name
            FROM detections
            {where_clause}
            GROUP BY species
        """, params).fetchone()

        # Close database connection after query execution
        conn.close()

        # Return failure response if species is not found
        if not row:
            return jsonify(ok=False)

        # Return species details as JSON response
        return jsonify(
            ok=True,
            species=row[0],
            total_detections=row[1],
            first_detected=row[2].isoformat() if row[2] else None,
            last_detected=row[3].isoformat() if row[3] else None,
            stations=row[4],
            png_url=row[5],
            soundscape_url=row[6],
            scientific_name=row[7]
        )
    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))


# =========================================================
# UNIQUE SPECIES LIST FOR MONITOR SPOTLIGHT
# =========================================================
# API endpoint for retrieving species spotlight data
@app.get("/unique-species-list")
def unique_species_list():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()


        # Retrieve unique bird species with detection counts and images
        rows = cursor.execute("""
            SELECT 
                species,
                COUNT(*) as total_detections,
                MAX(CASE 
                    WHEN png_url LIKE 'https://media.birdweather.com%' THEN png_url
                END) as png_url
            FROM detections
            WHERE species IS NOT NULL
            AND species NOT IN ('American Bullfrog', 'American Toad', 'Coyote', 'Dog', 'Eastern Gray Squirrel', 'Engine', 'Gray Treefrog', 'Spring Peeper')
            GROUP BY species
            ORDER BY total_detections DESC
        """).fetchall()

        # Close database connection after query execution
        conn.close()

        # Return formatted spotlight data
        return jsonify(ok=True, rows=[
            {
                "species": r[0],
                "count": r[1],
                "png_url": r[2]
            }
            for r in rows
        ])
    
    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))
    
# =========================================================
# BEST HOURS TO WATCH
# =========================================================
# API endpoint for identifying the most active bird detection hours
@app.get("/best-hours")
def best_hours():
    try:

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Count detections for each hour of the day
        rows = cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/New_York')::INTEGER as hour,
                COUNT(*) as cnt
            FROM detections
            WHERE timestamp IS NOT NULL
            AND species NOT IN ('American Bullfrog', 'American Toad', 'Coyote', 'Dog', 'Eastern Gray Squirrel', 'Engine', 'Gray Treefrog', 'Spring Peeper')
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        # Close database connection after query execution
        conn.close()

        # Initialize all 24 hours with zero detections
        hour_counts = {hour: 0 for hour in range(24)}

        # Fill available hours with actual detection counts
        for hour, cnt in rows:
            if hour is not None:
                hour_counts[hour] = cnt

        # Select top 3 hours with the highest detection activity
        top_hours = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]


        # Format top hours for display cards
        formatted_top_hours = []

        for hour, _ in top_hours:
            if hour == 0:
                label = "12 AM"
            elif hour < 12:
                label = f"{hour} AM"
            elif hour == 12:
                label = "12 PM"
            else:
                label = f"{hour - 12} PM"

            formatted_top_hours.append(label)


        # Prepare hourly chart labels and values
        chart_labels = []
        chart_counts = []

        for hour in range(24):
            if hour == 0:
                label = "12A"
            elif hour < 12:
                label = f"{hour}A"
            elif hour == 12:
                label = "12P"
            else:
                label = f"{hour - 12}P"

            chart_labels.append(label)
            chart_counts.append(hour_counts[hour])

        # Return best-hour summary and chart data
        return jsonify(
            ok=True,
            hours=formatted_top_hours,
            chart_labels=chart_labels,
            chart_counts=chart_counts
        )

    # Handle unexpected application errors 
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# =========================================================
# NEXT HOUR ACTIVITY FORECAST
# =========================================================
# API endpoint for predicting expected bird activity in the next hour
@app.get("/activity-forecast")
def activity_forecast():
    try:

        # Establish database connection
        conn = get_db_connection()
        
        # Load detection timestamps into a dataframe for time-based modeling
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT timestamp
                FROM detections
                WHERE timestamp IS NOT NULL
            """)
            rows = cursor.fetchall()


        # Close database connection after reading data
        conn.close()

        df = pd.DataFrame(rows, columns=["timestamp"])

        # Convert timestamp values into timezone-aware datetime format
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
            utc=True
        )

        # Remove invalid timestamp records
        df = df.dropna(subset=["timestamp"])

        # Group detections into hourly time buckets
        df["hour_bucket"] = df["timestamp"].dt.floor("h")

        # Count detections for each hour
        hourly = (
            df.groupby("hour_bucket")
            .size()
            .reset_index(name="detection_count")
            .sort_values("hour_bucket")
        )

        # Create time-based prediction features
        hourly["hour"] = hourly["hour_bucket"].dt.hour
        hourly["day_of_week"] = hourly["hour_bucket"].dt.dayofweek
        hourly["month"] = hourly["hour_bucket"].dt.month

        # Create recent-activity features from previous detection counts
        hourly["prev_hour_count"] = hourly["detection_count"].shift(1)
        hourly["prev_3hr_avg"] = hourly["detection_count"].shift(1).rolling(3).mean()

        # Remove rows without enough previous-hour history
        hourly = hourly.dropna()


        # Convert detection count into activity category
        def label_activity(count):
            if count <= 30:
                return 0
            elif count <= 80:
                return 1
            else:
                return 2

        # Assign activity labels for model training
        hourly["activity_level"] = hourly["detection_count"].apply(label_activity)

        # Model input features
        X = hourly[[
            "hour",
            "day_of_week",
            "month",
            "prev_hour_count",
            "prev_3hr_avg"
        ]]

        # Target activity label
        y = hourly["activity_level"]

        # Initialize Random Forest classification model
        model = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )

        model.fit(X, y)                                         # Train model using historical hourly activity patterns

        
        latest = hourly.iloc[-1]                                # Get latest available hourly activity record
        next_hour_time = latest["hour_bucket"] + pd.Timedelta(hours=1)  # Create next-hour timestamp for prediction

        # Prepare next-hour feature values
        X_next = pd.DataFrame([{
            "hour": next_hour_time.hour,
            "day_of_week": next_hour_time.dayofweek,
            "month": next_hour_time.month,
            "prev_hour_count": latest["detection_count"],
            "prev_3hr_avg": hourly["detection_count"].tail(3).mean()
        }])

        prediction = model.predict(X_next)[0]                   # Predict next-hour activity class

        # Calculate prediction confidence percentage
        probabilities = model.predict_proba(X_next)[0]
        confidence = round(probabilities[prediction] * 100)

        # Map numeric model output to readable activity labels
        labels = {
            0: "Low Activity",
            1: "Normal Activity",
            2: "High Activity"
        }

        # Return forecast result as JSON response
        return jsonify(
            ok=True,
            activity=labels[prediction],
            confidence=confidence
        )
    # Handle unexpected application errors
    except Exception as e:
        return jsonify(ok=False, error=str(e))


# =========================================================
# MAIN APPLICATION ENTRY POINT
# =========================================================
# Run Flask application on local network
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
