import httpx
import time
import asyncio


async def test():
    url = "http://localhost:8000/schedules"
    payload = {
        "name": "test-job-py",
        "schedule": "@every 5s",
        "action": "py_test_action",
        "params": {"source": "python_script"},
    }
    headers = {"X-User-ID": "user_py"}

    async with httpx.AsyncClient() as client:
        try:
            print("Sending request...")
            resp = await client.post(url, json=payload, headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test())
