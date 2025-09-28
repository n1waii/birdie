# config.py
import json

DEFAULT_CONFIG = {
    "manual_sensitivity": 1.0,
    "socket_max_power": 800,
    "simulator_angle_cycle_seconds": 10.0,
    "simulator_power_cycle_seconds": 3.0,
    "friction": 0.992,

    # ===== Sensitivity and IMU controls =====
    "aim_axis": "x",
    "gyro_rate_is_rad_per_s": True,
    "aim_deadzone_dps": 300,
    "aim_wrap_deg": 180.0,
    'power_yaw_axis': 'y',

    "bias_max_samples": 60,
    "bias_gyro_steady_dps": 3.0,
    "bias_accel_steady_g": 0.12,

    "accel_baseline_alpha": 0.10,
    "mag_baseline_alpha": 0.10,

    "accel_swing_axis": "z",
    "swing_down_trig_axis_g": -0.35,
    "swing_down_trig_mag_g": -0.25,
    "swing_end_threshold_g": 0.12,
    "swing_max_window_s": 0.50,

    "power_peak_min_g": 0.25,
    "power_peak_max_g": 1.80,
    "power_smoothing_alpha": 0.25,
    "snap_power_on_shoot": True,
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
