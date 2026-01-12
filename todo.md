# TODO

the purpose of this repo is to explore scheduler where users can schedule tasks to run on a regular basis.

the schedule is an interval of time such as every 5 minutes, every day, or every monday Wednesday and Friday at 9 AM, or every week on Monday at 9 AM.

one users can set multiple schedules.

the scheduler perform action via webhook such as

/localhost:8000/action/webhook 
with json body
{
    "action": "action_name",
    "params": {
        "param1": "value1",
        "param2": "value2"
    }
}


use dkron from https://github.com/distribworks/dkron deployed via docker compose 
documentation can be found at: https://dkron.io/docs/basics/getting-started 
The dkron API should use port localhost:8089

users should be able to do
- create schedule (interval, action, params)
- update schedule (interval)
- delete schedule 
- list schedules that they created

then create a basic web backend in python with the webhook that
for now will just log the action and params

def webhook(action, params):
    logging.info(f"action: {action}, params: {params}")

right now this is just a mock POC to explore dkron

---
Questions:

Q1: How should we identify "users" in this POC? Should we use a simple header like `X-User-ID`, or is multi-user isolation not a priority for the initial mock?

use X-User-ID header, but know that this is not a priority for the initial mock. just that dkron should be able to identify the user, and support multiple users.

Q2: For the schedule intervals (e.g., "every Monday Wednesday and Friday at 9 AM"), should we use standard Cron expressions or Dkron's specific interval strings?

use Dkron's specific cron expression!

Q3: Should the Python backend also be responsible for calling the Dkron API to create/update schedules, or are we focusing on the manual setup and webhook logging for now?

Yes the python backend should be responsible for calling the dkron scheduling API to create update delete and modify schedules.