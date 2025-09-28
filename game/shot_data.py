# shot_data.py
import time
import math
from config import CONFIG # Import the config object

def get_latest_shot_data():
    """
    Simulates a continuous stream of data from a socket.
    The oscillation speeds are now controlled by config.json.
    """
    current_time = time.time()
    
    # Use config values to determine oscillation frequency
    angle_freq = (2 * math.pi) / CONFIG['simulator_angle_cycle_seconds']
    power_freq = (2 * math.pi) / CONFIG['simulator_power_cycle_seconds']
    
    angle_radians = math.pi * math.sin(current_time * angle_freq / (2 * math.pi))
    power_normalized = 0.1 + 0.9 * ((math.sin(current_time * power_freq / (2 * math.pi)) + 1) / 2)

    return {
        "angle": angle_radians,
        "power": power_normalized
    }