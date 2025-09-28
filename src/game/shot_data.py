# shot_data.py
import time
import math
from config import CONFIG # Assuming you still use this for fallback

# IMPORTANT: Change this to the axis that represents your putt's swing ('x', 'y', or 'z')
# You can find this by printing the data while swinging the club to see which value changes most.
SWING_AXIS = 'y' 

# This variable will store the angle at the beginning of the swing.
start_angle = 0
is_swing_started = False

def start_new_swing():
    """
    Call this function from your game logic to reset the angle for a new putt.
    """
    global is_swing_started
    is_swing_started = False
    print("Ready for a new swing. Angle has been zeroed.")

def get_latest_shot_data(sensor_server):
    """
    Processes the latest sensor data to get the current putt angle relative to
    the start of the swing.
    """
    global start_angle, is_swing_started
    
    # 1. Fetch the complete data object from your server
    data = sensor_server.get_latest_data()
    
    # If no data has arrived yet, return a default or simulated value
    if not data:
        # This part is your original simulator code, good for a fallback.
        current_time = time.time()
        angle_freq = (2 * math.pi) / CONFIG['simulator_angle_cycle_seconds']
        angle_radians = math.pi * math.sin(current_time * angle_freq / (2 * math.pi))
        return {"angle": angle_radians, "power": 0} # Simplified fallback

    try:
        # 2. Extract the ever-increasing absolute angle from the ESP32
        # This value is already in degrees.
        current_absolute_angle = data['gyroscope_absolute'][SWING_AXIS]

        # 3. Handle the "resetting" of the angle for a new swing
        # if not is_swing_started:
        #     # This is the first data point for a new swing.
        #     # Record the current angle as our new "zero" point.
        #     start_angle = current_absolute_angle
        #     is_swing_started = True

        # The actual putt angle is the difference from where the swing started.
        putt_angle_degrees = current_absolute_angle - start_angle
        
        # Your game might need the angle in radians
        putt_angle_radians = math.radians(putt_angle_degrees)

        # You can add logic for power based on accelerometer or gyro rate later
        # For now, let's just return the angle.
        return {
            "angle": putt_angle_radians, 
            "power": 0 # Placeholder for power
        }

    except (KeyError, TypeError):
        # This can happen if the JSON is malformed or doesn't have the expected keys
        print("Warning: Received data is not in the expected format.")
        return {"angle": 0, "power": 0}
