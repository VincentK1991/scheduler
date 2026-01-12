from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from contextlib import asynccontextmanager
import logging
from .database import engine, SQLALCHEMY_DATABASE_URL, Base
from .routes import router, set_scheduler, execute_webhook, get_trigger
from .models import Schedule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
# In a real app, use Alembic migrations. For POC, this is fine.
Base.metadata.create_all(bind=engine)

# Configure APScheduler with SQLAlchemy JobStore
# This jobstore is for APScheduler's INTERNAL job tracking (next run time, etc.)
# We also have our own Schedule model for the user-facing API.
# Ideally, we sync them or use one source of truth.
# For this task, "users should be able to create schedule... persist in database".
# We use our own DB table for the API resource, and let APScheduler manage its own persistence
# or we can just use APScheduler's memory store if we reload from our DB on startup.
# But `TODO2.md` mentions `SQLAlchemyJobStore`.
#
# If we use `SQLAlchemyJobStore`, APScheduler creates its own tables (`apscheduler_jobs`).
#
# Strategy:
# 1. We keep `schedules` table for our API/Business logic.
# 2. We use `SQLAlchemyJobStore` for APScheduler to ensure jobs survive restarts even if we don't manually reload them.
# 3. BUT, simple approach:
#    - Use `SQLAlchemyJobStore`.
#    - When our app starts, APScheduler will load jobs from its table.
#    - When we access our API, we touch our `schedules` table.
#    - In `routes.py`, we update both.

jobstores = {
    'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URL)
}

scheduler = BackgroundScheduler(jobstores=jobstores)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler
    scheduler.start()
    
    # Pass scheduler to router
    set_scheduler(scheduler)
    
    # Sync check (Optional):
    # In a robust system, we might check if our `Schedule` table matches `scheduler.get_jobs()`.
    # For now, we assume they are kept in sync via the API.
    
    yield
    scheduler.shutdown()

app = FastAPI(title="Persistent Scheduler V2", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
