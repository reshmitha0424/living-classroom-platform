# Living Classroom Platform

Living Classroom Platform is a Flask-based bird activity monitoring and analytics dashboard developed for the University of Delaware Living Classroom project. It collects live and historical detection data from BirdWeather, stores detections in PostgreSQL, and provides interactive dashboards for viewing species activity, station locations, detection trends, and short-term activity forecasts.

## Features

- Live BirdWeather detection ingestion
- Historical detection retrieval by date range
- PostgreSQL storage with duplicate protection
- Multi-station live monitoring
- Dedicated monitor dashboard with QR-code access
- Latest-detection and summary statistics
- Species rankings and detailed species views
- Monthly and hourly activity analysis
- Detection location mapping
- Species activity timelines
- Next-hour activity forecasting
- Responsive monitoring and interactive dashboards

## Architecture

```text
BirdWeather API
        ↓
ingest.py / pull_historicData.py
        ↓
PostgreSQL
        ↓
Flask
        ↓
Browser Dashboard
```

## Project Structure

```text
.
├── app.py                     # Flask application and dashboard APIs
├── ingest.py                  # Continuous live detection ingestion
├── pull_historicData.py       # Historical BirdWeather ingestion
├── database_postgres.py       # PostgreSQL schema initialization
├── db_config.py               # Environment-based configuration
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment configuration
├── templates/                 # Flask HTML templates
├── static/                    # JavaScript, styles, and visual assets
├── scripts/offline/           # Offline analysis and model scripts
├── data/reference/            # Reference datasets
└── archive/                   # Legacy scripts and SQLite databases
```

## Technology Stack

- Python
- Flask
- PostgreSQL
- Psycopg 3
- pandas
- scikit-learn
- BirdWeather API
- HTML, CSS, and JavaScript

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the following variables using your own values:

```dotenv
BIRDWEATHER_AUTH_KEY=your_birdweather_auth_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

Do not commit `.env`.

## Initialize PostgreSQL

Create the PostgreSQL database specified by `DB_NAME`, then initialize the `detections` table and unique index:

```bash
python database_postgres.py
```

Expected output:

```text
PostgreSQL detections table initialized successfully.
```

## Run Live Ingestion

Start continuous ingestion for the configured BirdWeather stations:

```bash
python ingest.py
```

The process polls the BirdWeather API every 60 seconds and inserts new detections into PostgreSQL. Duplicate detections are ignored.

Stop the process with `Ctrl+C`.

## Run Historical Ingestion

Set the required date range in `pull_historicData.py`:

```python
FROM_DATE = "YYYY-MM-DD"
TO_DATE = "YYYY-MM-DD"
```

Then run:

```bash
python pull_historicData.py
```

The script processes the inclusive date range one day at a time and retrieves detections in hourly windows. Existing detections are ignored through PostgreSQL conflict handling.

## Start the Flask Application

Run:

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

Available dashboards:

- `/` — monitoring dashboard
- `/dashboard` — interactive analytics dashboard

## Screenshots

Coming soon.

## Current Limitations

- Historical ingestion is configured for one BirdWeather station.
- Historical requests return at most 100 detections per hourly window; busy hours are reported but not automatically subdivided.
- Ingestion scripts have limited retry and resume handling.
- The Flask development server is not intended for production use.
- Activity forecasting trains a model during API requests rather than loading a pre-trained model.
- Offline analysis scripts still use the archived SQLite workflow.

## Roadmap

- [ ] Add configurable multi-station historical ingestion
- [ ] Add automatic pagination or smaller windows for busy historical periods
- [ ] Add retry, resume, and structured logging support
- [ ] Package the application for Docker deployment
- [ ] Deploy behind a production WSGI server
- [ ] Add managed production hosting and PostgreSQL
- [ ] Expand dashboard filters, visualizations, and station comparisons
- [ ] Move forecasting to a scheduled training pipeline
- [ ] Add automated tests and continuous integration
