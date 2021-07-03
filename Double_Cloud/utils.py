import json
import time
current_time = lambda: int(round(time.time() * 1000))

def load_json(dir):
    with open(dir, 'r') as f:
        config = json.load(f)
    return config

def time_print(m):
    print(m + " time:" + str(current_time()))
