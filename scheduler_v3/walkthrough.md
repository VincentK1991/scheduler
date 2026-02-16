# Scheduler V3 Walkthrough (Temporal)

This document explains the architecture and flow of `scheduler_v3`, which uses Temporal to manage distributed scheduling and task execution.

## System Components

1.  **User / Frontend**: Clients interacting with the HTTP API (e.g., `curl`, Postman, or a web UI).
2.  **Main Backend (`main.py`)**: FastAPI application.
    -   Manages application-specific metadata in PostgreSQL (`schedules` table).
    -   Acts as a **Temporal Client**, creating and updating Schedules in the Temporal Cluster.
3.  **Temporal Server**: The core Temporal Cluster (Frontend, History, Matching, Worker services).
    -   Manages the state of Schedules, Workflows, and Activities.
    -   Persists state to its own PostgreSQL database.
4.  **Worker (`worker.py`)**: A Python process running the Temporal Worker.
    -   Polls the `scheduler-v3-task-queue`.
    -   Executes the `PrintWorkflow` and `print_activity`.

## Sequence Diagram

The following diagram illustrates the lifecycle of a schedule: from creation to execution.

```mermaid
sequenceDiagram
    autonumber
    participant U as User / Frontend
    participant B as Main Backend (FastAPI)
    participant DB as App DB (Postgres)
    participant T as Temporal Server
    participant W as Temporal Worker

    Note over U, T: Phase 1: Create Schedule
    U->>B: POST /schedules (cron, payload)
    B->>DB: INSERT Schedule metadata
    DB-->>B: Schedule ID
    B->>T: client.create_schedule(id, cron, workflow="PrintWorkflow")
    T-->>B: Schedule Created
    B-->>U: 200 OK (Schedule JSON)

    Note over T, W: Phase 2: Async Execution (Triggered by Cron)
    
    loop Every Cron Interval
        T->>T: Timer Fires
        T->>T: Enqueue Workflow Task (Queue: scheduler-v3-task-queue)
        
        W->>T: Poll Task Queue
        T-->>W: Workflow Task (PrintWorkflow)
        
        activate W
        W->>W: Run Workflow Logic
        W->>T: Request Activity Execution (print_activity)
        T-->>W: Activity Task
        
        W->>W: Execute print_activity
        Note right of W: Prints payload to stdout / calls webhook
        
        W->>T: Complete Activity
        W->>T: Complete Workflow
        deactivate W
    end
```

## Key Workflows

### 1. Creating a Schedule
When `POST /schedules` is called:
1.  **Local Persistence**: The schedule details (Cron, URL, Payload) are saved to the local application database for querying and UI display.
2.  **Temporal Schedule**: A corresponding **Temporal Schedule** is created using the same ID. This object lives on the Temporal Server and manages the timing.
    -   It is configured to trigger `PrintWorkflow` at the specified intervals.

### 2. Execution
At the scheduled time:
1.  **Temporal Server** triggers the schedule.
2.  It starts a new execution of `PrintWorkflow`.
3.  This places a task on the `scheduler-v3-task-queue`.
4.  The **Worker** (which could be running on any machine) picks up the task.
5.  The Worker executes the `print_activity`, which currently prints the payload to the console.
    -   *In a real scenario, this would perform the actual HTTP webhook call.*

### 3. Updating / Deleting
-   **Update**: Updates both the local DB record and the Temporal Schedule spec (e.g., changing the Cron expression).
-   **Delete**: Deletes the local DB record and triggers a deletion of the Temporal Schedule.
