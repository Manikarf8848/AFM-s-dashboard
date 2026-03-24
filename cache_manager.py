# Cache Manager

"""
This module provides memory management and caching utilities for the AFM Dashboard.
"""

import json
import os
import time
from functools import wraps

CACHE_DIR = 'cache'

# Ensure the cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


def cache_result(timeout=60):
    """
    Decorator to cache the result of a function call.
    """  
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_filename = os.path.join(CACHE_DIR, f'{func.__name__}.cache')
            # Check if cache file exists and is not expired
            if os.path.exists(cache_filename):
                with open(cache_filename, 'r') as f:
                    cache_time, result = json.load(f)
                if time.time() - cache_time < timeout:
                    return result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            with open(cache_filename, 'w') as f:
                json.dump((time.time(), result), f)
            return result
        return wrapper
    return decorator


def clear_cache():
    """
    Clears the cache directory.
    """
    for filename in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, filename)
        os.remove(file_path)  


# Example usage:
@cache_result(timeout=300)
def expensive_computation(param):
    # Simulate an expensive computation
    time.sleep(2)
    return param ** 2

if __name__ == '__main__':
    print(expensive_computation(5))  # This will take time on first call
    print(expensive_computation(5))  # This will use cache
