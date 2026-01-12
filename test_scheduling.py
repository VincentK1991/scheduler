import httpx
import time

def create_test_schedule():
    url = "http://localhost:8090/schedules"
    
    payload = {
        "cron_expression": "@every 10s",
        "webhook_url": "http://localhost:8000/action/webhook",
        "webhook_payload": {
            "name": "test-job-py",
            "action": "another action",
            "params": {"source": "python_script3"}
        }
    }
    
    headers = {
        "X-User-ID": "test-user-script",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Creating schedule at {url}...")
        response = httpx.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("Schedule created successfully!")
        print(response.json())
        
        print("\nWaiting for webhooks... (Press Ctrl+C to stop)")
        while True:
            time.sleep(1)
            
    except httpx.HTTPError as e:
        print(f"HTTP Error: {e}")
        if hasattr(e, 'response'):
            print(f"Response: {e.response.text}")
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    create_test_schedule()
