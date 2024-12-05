import time
from functools import wraps
import json

# Dictionary to store the execution time of each function
execution_times = {}


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        func_name = f"{func.__module__}.{func.__qualname__}"
        # Store the execution time
        if func_name in execution_times:
            execution_times[func_name] += elapsed_time
        else:
            execution_times[func_name] = elapsed_time
        return result

    return wrapper


def save_execution_times(filename='execution_times.json'):
    with open(filename, 'w') as f:
        json.dump(execution_times, f, indent=4)


def apply_decorator_to_class(cls):
    for attr in dir(cls):
        if callable(getattr(cls, attr)) and not attr.startswith("__"):
            original_func = getattr(cls, attr)
            decorated_func = timeit(original_func)
            setattr(cls, attr, decorated_func)
    return cls


def apply_decorator_to_module(module):
    for attr in dir(module):
        if not attr.startswith("__"):
            module_attr = getattr(module, attr)
            if callable(module_attr):
                setattr(module, attr, timeit(module_attr))
            elif isinstance(module_attr, type):
                apply_decorator_to_class(module_attr)
