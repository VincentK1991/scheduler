from temporalio import activity
import random
import os

@activity.defn
async def activity_a(payload: dict) -> str:
    activity.logger.info(f"Executed A on PID {os.getpid()} with {payload}")
    return "Result_A"

@activity.defn
async def activity_b(input_val: str) -> str:
    activity.logger.info(f"Executed B on PID {os.getpid()} with {input_val}")
    # return "Result_B"
    if random.random() < 0.2: # 20% failure chance
         raise Exception("Random failure in B")
    return "Result_B"

@activity.defn
async def activity_d(input_val: str) -> str:
    activity.logger.info(f"Executed D on PID {os.getpid()} with {input_val}")
    return "Result_D"

@activity.defn
async def activity_e(inputs: dict) -> str:
    activity.logger.info(f"Executed E on PID {os.getpid()} with {inputs}")
    if random.random() < 0.2: # 20% failure chance
         raise Exception("Random failure in E")
    return "Result_E"

# Compensations
@activity.defn
async def compensate_a(arg: str) -> str:
    activity.logger.info("Compensated A")
    return "Compensated_A"

@activity.defn
async def compensate_b(arg: str) -> str:
    activity.logger.info("Compensated B")
    return "Compensated_B"

@activity.defn
async def compensate_d(arg: str) -> str:
    activity.logger.info("Compensated D")
    return "Compensated_D"

@activity.defn
async def compensate_e(arg: str) -> str:
    activity.logger.info("Compensated E")
    return "Compensated_E"
