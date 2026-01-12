# Scheduler POC

This project implements a POC for a scheduler using Dkron and FastAPI.

## Prerequisites
- Docker
- Python 3.12
- uv

## Getting Started

1. Start Dkron:
   ```bash
   docker compose up -d
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the server:
   ```bash
   uv run uvicorn server:app --reload
   ```
