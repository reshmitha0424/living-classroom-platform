# Project Structure

The repository keeps its deployable process entry points at the root so each service has a clear, direct command. Flask templates and static assets follow the conventional Flask directory layout. Research utilities and legacy files are separated from the active PostgreSQL workflow.

## Active application files

- `app.py` — Flask application, dashboard pages, JSON API routes, PostgreSQL queries, and activity forecasting. The production WSGI target is `app:app`.
- `continuous_ingestion.py` — continuously polls the configured BirdWeather station IDs and writes new detections to PostgreSQL.
- `historical_ingestion.py` — performs a one-time historical BirdWeather import for its configured station and date range.
- `initialize_database.py` — creates the PostgreSQL `detections` table and unique index when they do not already exist.
- `database_config.py` — loads PostgreSQL connection settings from environment variables, with local `.env` support.
- `requirements.txt` — pinned Python runtime dependencies.

## Web interface

- `templates/dashboard.html` — interactive analytics dashboard at `/dashboard`.
- `templates/monitor_dashboard.html` — monitoring display at `/`.
- `static/dashboard.js` and `static/dashboard.css` — interactive dashboard behavior and styling.
- `static/monitor_dashboard.js` and `static/monitor_dashboard.css` — monitoring display behavior and styling.
- `static/qr/dashboard_qr.png` — QR image displayed on the monitoring page.

## Supporting and non-production files

- `data/reference/` — reference datasets retained for research or recovery; these are not used by the active application.
- `scripts/offline/` — standalone analysis utilities that still use the legacy SQLite workflow and are not part of the deployed services.
- `archive/legacy_scripts/` — superseded API and SQLite scripts retained for historical reference.
- `archive/sqlite_databases/` — ignored legacy SQLite databases, replaced by PostgreSQL in the active workflow.

## Active process flow

```text
BirdWeather API
        |
continuous_ingestion.py / historical_ingestion.py
        |
PostgreSQL
        |
app.py (Flask/Gunicorn)
        |
Browser dashboards
```
