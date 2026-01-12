import json
import logging
import os
from typing import Any, Dict, Optional, cast

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduler POC")

# Dkron Configuration
DKRON_URL = os.getenv("DKRON_URL", "http://localhost:8089")
# Local host for Dkron to call back.
# "host.docker.internal" is used by Docker container to reach host on Windows/Mac.
# If running Dkron on Linux without this DNS, might need the actual IP.
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://host.docker.internal:8000")


class ScheduleParams(BaseModel):
    param1: Optional[str] = None
    param2: Optional[str] = None


class ActionPayload(BaseModel):
    action: str
    params: Dict[str, Any]


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., description="Unique name for the schedule")
    schedule: str = Field(
        ..., description="Dkron interval string or cron expression e.g. @every 1m"
    )
    action: str = Field(..., description="Action name to be logged")
    params: Dict[str, Any] = Field(default_factory=dict)


# Webhook Endpoint
@app.post("/action/webhook")
async def webhook(payload: ActionPayload):
    logger.info(
        f"Received webhook trigger! Action: {payload.action}, Params: {payload.params}"
    )
    return {"status": "received", "payload": payload.model_dump()}


# Dkron Proxy / Schedule Management


@app.post("/schedules")
async def create_schedule(
    req: CreateScheduleRequest, x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        # For this POC, we can allow missing user ID or warn. Let's log it.
        logger.warning("No X-User-ID header provided.")

    # Construct the job for Dkron
    # Dkron job structure: https://dkron.io/docs/usage/api/#create-a-job
    # query args used for the webhook

    # We will use the 'http' executor of Dkron to call our webhook

    job_name = f"{x_user_id}_{req.name}" if x_user_id else req.name

    webhook_url = f"{WEBHOOK_BASE_URL}/action/webhook"

    # Serialize the body content safely
    webhook_body = json.dumps({"action": req.action, "params": req.params})

    job_payload = {
        "name": job_name,
        "schedule": req.schedule,
        "executor": "http",
        "executor_config": {
            "method": "POST",
            "url": webhook_url,
            "headers": '["Content-Type: application/json"]',
            "body": webhook_body,
            "timeout": "10s",
            "expectCode": "200",
        },
        "metadata": {"user_id": x_user_id or "anonymous"},
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{DKRON_URL}/v1/jobs", json=job_payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Dkron error: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Dkron error: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/schedules")
async def list_schedules(
    x_user_id: Optional[str] = Header(None),
    metadata: Optional[str] = Query(
        None, description="JSON string of metadata to filter by"
    ),
):
    query_params: Dict[str, Any] = {}

    # Filter by user_id if provided (legacy header support)
    if x_user_id:
        query_params["metadata[user_id]"] = x_user_id

    # Filter by generic metadata if provided
    if metadata:
        try:
            meta_dict = json.loads(metadata)
            if isinstance(meta_dict, dict):
                # cast for pyright strictness on k, v
                typed_meta = cast(Dict[str, Any], meta_dict)
                for k, v in typed_meta.items():
                    query_params[f"metadata[{k}]"] = v
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{DKRON_URL}/v1/jobs", params=query_params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.delete("/schedules/{name}")
async def delete_schedule(name: str, x_user_id: Optional[str] = Header(None)):
    job_name = f"{x_user_id}_{name}" if x_user_id else name
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(f"{DKRON_URL}/v1/jobs/{job_name}")
            resp.raise_for_status()
            return {"status": "deleted", "job": job_name}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
