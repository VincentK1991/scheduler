from temporalio import activity

@activity.defn
async def print_activity(message: str) -> str:
    activity.logger.info(f"Activity execution: {message}")
    print(f"Printing: {message}")
    return f"Printed: {message}"
