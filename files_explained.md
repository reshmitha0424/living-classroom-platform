## Active workflow files

These are part of the PostgreSQL application:

- `app.py` — Flask dashboard and API routes.
- `ingest.py` — live BirdWeather ingestion.
- `pull_historicData.py` — historical API ingestion.
- `database_postgres.py` — creates the PostgreSQL table and index.
- `db_config.py` — shared PostgreSQL connection settings.
- `templates/` — Flask HTML templates.
- `static/` — dashboard JavaScript and CSS.

## Good to keep, but outside the active workflow

- `combined_birdweather_data.csv` — useful as a backup/reference dataset, even if historical data will come from the API.
- `best_birdwatching_hours.py` — standalone CSV reporting utility; dashboard already provides similar information.
- `train_activity_model.py` — offline model evaluation and diagnostics; not used by the running dashboard.
- `.vscode/` — editor configuration; not required at runtime.

These two scripts still use SQLite. They must be migrated before running them against PostgreSQL.

## Obsolete or replaceable

- `database.py` — old initializer for `birds.db`.
- `database_v2.py` — obsolete duplicate of `database_postgres.py`; it also contains hard-coded credentials and should be removed or sanitized.
- `birdweather_pull.py` — early single-station API testing loop, superseded by `ingest.py`.
- `load_data.py` — old SQLite CSV importer. It is unnecessary if historical data will be pulled from the API.
- `birds.db` — original SQLite database.
- `birds_v2.db` — newer SQLite database, now replaced by PostgreSQL.
- `__pycache__/` — generated Python bytecode cache; safe to regenerate.
