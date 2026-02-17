from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from temporalio.client import Client

from .database import engine, Base
from .routes import router, set_temporal_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Temporal
    try:
        client = await Client.connect("localhost:7233")
        set_temporal_client(client)
        logger.info("Connected to Temporal Server")
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        # We might want to exit here or retry, but for POC we allow start so we can debug
    
    yield
    # Cleanup if needed

app = FastAPI(title="Temporal Scheduler V3", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
