import json


def load_json(dir):
    with open(dir, 'r') as f:
        config = json.load(f)
    return config

