from fastapi import FastAPI
from contextlib import asynccontextmanager
from temporalio.client import Client
from .routes import router, set_temporal_client
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Temporal
    try:
        client = await Client.connect("localhost:7233")
        set_temporal_client(client)
        logging.info("Connected to Temporal Server")
    except Exception as e:
        logging.error(f"Failed to connect to Temporal: {e}")
        
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)
