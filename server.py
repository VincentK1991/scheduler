import logging
import os
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduler V2 Worker")


class ActionPayload(BaseModel):
    action: str
    params: Dict[str, Any]


# Webhook Endpoint
@app.post("/action/webhook")
async def webhook(payload: ActionPayload):
    logger.info(
        f"Received webhook trigger! Action: {payload.action}, Params: {payload.params}"
    )
    return {"status": "received", "payload": payload.model_dump()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
