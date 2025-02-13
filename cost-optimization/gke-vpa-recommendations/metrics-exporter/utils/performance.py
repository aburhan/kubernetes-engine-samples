import time
import psutil
import os
from functools import wraps

def profile_execution(func):
    """
    Decorator to profile execution time, memory, and CPU usage of a function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the process info
        process = psutil.Process(os.getpid())
        
        # Record start time, memory, and CPU usage
        start_time = time.perf_counter()
        start_memory = process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
        start_cpu = process.cpu_percent(interval=None)
        
        # Run the actual function
        result = func(*args, **kwargs)
        
        # Record end time, memory, and CPU usage
        end_time = time.perf_counter()
        end_memory = process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
        end_cpu = process.cpu_percent(interval=None)
        
        # Calculate metrics
        exec_time = end_time - start_time
        memory_usage = end_memory - start_memory
        cpu_usage = end_cpu
        
        # Print the results
        print(f"Function '{func.__name__}' Execution Time: {exec_time:.4f} seconds")
        print(f"Memory Used: {memory_usage:.4f} MB")
        print(f"CPU Usage: {cpu_usage:.2f}%")
        
        return result
    
    return wrapper


