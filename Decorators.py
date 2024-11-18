from concurrent.futures import ThreadPoolExecutor
import functools
import asyncio

# Create a ThreadPoolExecutor instance
executor = ThreadPoolExecutor(max_workers=10)

# Define the decorator
def run_in_background(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Submit the function to the thread pool to run in the background
        future = executor.submit(func, *args, **kwargs)
        return future  # Returning the future allows tracking the task

    return wrapper
def run_in_background_async(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Schedule the async function to run in the background
        task = asyncio.create_task(func(*args, **kwargs))
        return task  # Return the task to allow tracking

    return wrapper


# # Example of using the decorator
# @run_in_background
# def long_running_task():
#     print("Started long task...")
#     import time
#     time.sleep(5)
#     print("Long task completed.")
#
# # Running the function in the background
# future = long_running_task()
#
# # Main thread can continue with other work
# print("Main thread continues while the task runs in the background.")
# future.result()
