# config.py
import json

DEFAULT_CONFIG = {
  "manual_sensitivity": 1.0,
  "socket_max_power": 800,
  "simulator_angle_cycle_seconds": 10.0,
  "simulator_power_cycle_seconds": 3.0,
  "friction": 0.992
}

def load_config(filepath: str) -> dict:
    """
    Loads the configuration from a JSON file.
    Returns default settings if the file is missing or invalid.
    """
    try:
        with open(filepath, 'r') as f:
            user_config = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        print("INFO: 'config.json' not found or invalid. Using default settings.")
        return DEFAULT_CONFIG

# Load the configuration once when the module is imported
CONFIG = load_config('src/game/config.json')