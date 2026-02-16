import random
from temporalio import activity

@activity.defn
async def activity_a(failure_rate: float) -> str:
    if random.random() < failure_rate:
        raise Exception("Random failure in Activity A")
    activity.logger.info("Executed Activity A")
    return "Result A"

@activity.defn
async def activity_b(failure_rate: float) -> str:
    if random.random() < failure_rate:
        raise Exception("Random failure in Activity B")
    activity.logger.info("Executed Activity B")
    return "Result B"

@activity.defn
async def activity_c(failure_rate: float) -> str:
    if random.random() < failure_rate:
        raise Exception("Random failure in Activity C")
    activity.logger.info("Executed Activity C")
    return "Result C"

@activity.defn
async def compensate_a() -> str:
    activity.logger.info("Compensated Activity A")
    return "Compensated A"

@activity.defn
async def compensate_b() -> str:
    activity.logger.info("Compensated Activity B")
    return "Compensated B"

@activity.defn
async def compensate_c() -> str:
    activity.logger.info("Compensated Activity C")
    return "Compensated C"
