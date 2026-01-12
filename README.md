# Scheduler Service

Persistent task scheduler using FastAPI, APScheduler, and PostgreSQL.

## Architecture

- **Web Server**: FastAPI
- **Scheduler**: APScheduler (AsyncIOScheduler) running in the background of the FastAPI app.
- **Database**: PostgreSQL (for job persistence)
- **Job Store**: SQLAlchemyJobStore

## Prerequisites

- Docker & Docker Compose
- Python 3.10+

## Running the Service

1. Start the database:
   ```bash
   docker-compose up -d
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or with uv
   uv sync
   ```

3. Run the application:
   ```bash
   uvicorn scheduler_v2.main:app --reload
   ```
bash
   uv run uvicorn server:app --reload
   ```
