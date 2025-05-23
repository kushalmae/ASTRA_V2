import os
import json

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'db_config.json')
    with open(config_path, "r") as f:
        return json.load(f)

config = load_config()
