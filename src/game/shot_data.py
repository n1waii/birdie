# shot_data.py
import time
import math
from config import CONFIG
import pygame
# =========================
#     CONFIG -> CONSTANTS
# =========================
AIM_AXIS = CONFIG.get('aim_axis', 'z')  # for aiming via gyro *rate*
POWER_YAW_AXIS = CONFIG.get('power_yaw_axis', 'y')  # absolute yaw axis for power

GYRO_RATE_IS_RAD_PER_S = bool(CONFIG.get('gyro_rate_is_rad_per_s', True))

ACCEL_SWING_AXIS = CONFIG.get('accel_swing_axis', 'z')

AIM_DEADZONE_DPS = float(CONFIG.get('aim_deadzone_dps', 1.0))
AIM_WRAP_DEG = float(CONFIG.get('aim_wrap_deg', 180.0))

BIAS_MAX_SAMPLES = int(CONFIG.get('bias_max_samples', 60))
BIAS_GYRO_STEADY_DPS = float(CONFIG.get('bias_gyro_steady_dps', 3.0))
BIAS_ACCEL_STEADY_G = float(CONFIG.get('bias_accel_steady_g', 0.12))

ACCEL_BASELINE_ALPHA = float(CONFIG.get('accel_baseline_alpha', 0.10))
MAG_BASELINE_ALPHA = float(CONFIG.get('mag_baseline_alpha', 0.10))

SWING_DOWN_TRIG_AXIS_G = float(CONFIG.get('swing_down_trig_axis_g', -0.35))
SWING_DOWN_TRIG_MAG_G  = float(CONFIG.get('swing_down_trig_mag_g', -0.25))
SWING_END_THRESHOLD_G  = float(CONFIG.get('swing_end_threshold_g', 0.12))
SWING_MAX_WINDOW_S     = float(CONFIG.get('swing_max_window_s', 0.50))

POWER_SMOOTHING_ALPHA = float(CONFIG.get('power_smoothing_alpha', 0.25))
SNAP_POWER_ON_SHOOT = bool(CONFIG.get('snap_power_on_shoot', True))

# Angle→power mapping
ANGLE_POWER_DEADZONE_DEG = float(CONFIG.get('angle_power_deadzone_deg', 3.0))
ANGLE_POWER_MAX_DEG      = float(CONFIG.get('angle_power_max_deg', 60.0))

# =========================
#          STATE
# =========================
_last_ts = None

# Aim (from gyro *rate*)
aim_angle_deg = 0.0
_gyro_bias_dps = 0.0
_bias_calibrating = True
_bias_sum_dps = 0.0
_bias_count = 0
_aim_lock_deg = 0.0  # frozen at arm

# Baselines
_accel_axis_baseline = None        # baseline for chosen axis (g-units)
_accel_mag_baseline = None         # baseline for |a| magnitude (g-units)

# Swing detection
_swing_armed = False
_swing_start_ts = 0.0
_peak_axis_hp = 0.0                 # most negative axis hp (<= 0)
_peak_mag_hp = 0.0                  # most negative mag hp (<= 0)

# UI smoothing
_smoothed_power = 0.0

# Absolute yaw for POWER only
_yaw_abs_deg = 0.0   # from gyroscope_absolute[POWER_YAW_AXIS] in degrees
_yaw_zero_deg = None # lazy baseline so neutral pose maps to power ~0

# =========================
#         HELPERS
# =========================
def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def _wrap_deg(a, lim=AIM_WRAP_DEG):
    span = 2.0 * lim
    return ((a + lim) % span) - lim

def _to_dps(rate_value):
    """Convert gyro rate to deg/s based on GYRO_RATE_IS_RAD_PER_S."""
    try:
        r = float(rate_value)
    except (TypeError, ValueError):
        return 0.0
    return math.degrees(r) if GYRO_RATE_IS_RAD_PER_S else r

def _accel_mag(ax, ay, az):
    return math.sqrt(ax * ax + ay * ay + az * az)

def _steady_enough_for_bias(gyro_dps, hp_mag):
    return abs(gyro_dps) <= BIAS_GYRO_STEADY_DPS and abs(hp_mag) <= BIAS_ACCEL_STEADY_G

def _angle_to_power(a_deg):
    if a_deg <= ANGLE_POWER_DEADZONE_DEG: return 0.0
    if a_deg >= ANGLE_POWER_MAX_DEG:      return 1.0
    return (a_deg - ANGLE_POWER_DEADZONE_DEG) / max(1e-6, (ANGLE_POWER_MAX_DEG - ANGLE_POWER_DEADZONE_DEG))

# =========================
#         API
# =========================
def start_new_swing():
    """Reset aim and swing detector for a new putt attempt."""
    global _last_ts, aim_angle_deg
    global _gyro_bias_dps, _bias_calibrating, _bias_sum_dps, _bias_count, _aim_lock_deg
    global _accel_axis_baseline, _accel_mag_baseline
    global _swing_armed, _swing_start_ts, _peak_axis_hp, _peak_mag_hp
    global _smoothed_power, _yaw_zero_deg

    _last_ts = None

    # Aim and bias
    aim_angle_deg = 0.0
    _gyro_bias_dps = 0.0
    _bias_calibrating = True
    _bias_sum_dps = 0.0
    _bias_count = 0
    _aim_lock_deg = 0.0

    # Baselines seeded lazily on first sample
    _accel_axis_baseline = None
    _accel_mag_baseline = None

    # Swing state
    _swing_armed = False
    _swing_start_ts = 0.0
    _peak_axis_hp = 0.0
    _peak_mag_hp = 0.0

    # UI
    _smoothed_power = 0.0

    # Power yaw baseline resets lazily
    _yaw_zero_deg = None

    print("Ready: aim reset; bias/baselines will auto-seed.")

# =========================
#     CORE PROCESSING
# =========================
def _integrate_aim(gyro_rate_value, accel, dt_s):
    """Integrate gyro rate into aim angle, with deadzone and bias removal."""
    global aim_angle_deg, _gyro_bias_dps, _bias_calibrating, _bias_sum_dps, _bias_count

    accelVec = pygame.math.Vector3(accel['x'], accel['y'], accel['z']) 
    accelMag = accelVec.magnitude()

    

    if dt_s <= 0:
        return

    dps_raw = _to_dps(gyro_rate_value)
    dps = dps_raw - _gyro_bias_dps

    # Deadzone
    if abs(dps) < AIM_DEADZONE_DPS:
        dps = 0.0
        print(abs(dps))

    # Integrate
    #print("a", accelMag)
    aim_angle_deg += dps * dt_s * .1 / (accelMag)
    aim_angle_deg = _wrap_deg(aim_angle_deg, AIM_WRAP_DEG) 

def _update_bias_and_baselines(accel, gyro_dps):
    """Seed and update baselines. Calibrate gyro bias when steady."""
    global _accel_axis_baseline, _accel_mag_baseline
    global _bias_calibrating, _bias_sum_dps, _bias_count, _gyro_bias_dps

    ax = float(accel.get('x', 0.0))
    ay = float(accel.get('y', 0.0))
    az = float(accel.get('z', 0.0))
    a_axis = float(accel.get(ACCEL_SWING_AXIS, 0.0))
    a_mag = _accel_mag(ax, ay, az)

    # Seed on first sample
    if _accel_axis_baseline is None:
        _accel_axis_baseline = a_axis
    if _accel_mag_baseline is None:
        _accel_mag_baseline = a_mag

    # Low-pass baselines
    _accel_axis_baseline += ACCEL_BASELINE_ALPHA * (a_axis - _accel_axis_baseline)
    _accel_mag_baseline += MAG_BASELINE_ALPHA * (a_mag - _accel_mag_baseline)

    # High-pass magnitude for steadiness check
    hp_mag = a_mag - _accel_mag_baseline

    # Bias calibration when steady
    if _bias_calibrating and _bias_count < BIAS_MAX_SAMPLES:
        if _steady_enough_for_bias(gyro_dps, hp_mag):
            _bias_sum_dps += gyro_dps
            _bias_count += 1
        if _bias_count >= BIAS_MAX_SAMPLES:
            _gyro_bias_dps = _bias_sum_dps / max(1, _bias_count)
            _bias_calibrating = False

    return (a_axis - _accel_axis_baseline), (a_mag - _accel_mag_baseline)

def _update_swing_detector(hp_axis, hp_mag, now_s):
    """
    Power is from absolute yaw angle relative to a baseline.
    Bar rises as yaw moves away from baseline and falls as it returns.
    Accel HP only arms/ends the stroke.
    """
    global _swing_armed, _swing_start_ts, _peak_axis_hp, _peak_mag_hp, _aim_lock_deg
    global _yaw_abs_deg, _yaw_zero_deg

    def yaw_rel_deg():
        # relative yaw magnitude in degrees, wrapped to [-AIM_WRAP_DEG, +AIM_WRAP_DEG]
        base = _yaw_zero_deg if _yaw_zero_deg is not None else _yaw_abs_deg
        return abs(_wrap_deg(_yaw_abs_deg - base, AIM_WRAP_DEG))

    shoot = False
    final_power = 0.0

    # Arm on downward accel deviation
    armed = (hp_axis <= SWING_DOWN_TRIG_AXIS_G) or (hp_mag <= SWING_DOWN_TRIG_MAG_G)
    if not _swing_armed and armed:
        _swing_armed = True
        _swing_start_ts = now_s
        _peak_axis_hp = min(0.0, hp_axis)
        _peak_mag_hp  = min(0.0, hp_mag)
        _aim_lock_deg = aim_angle_deg  # lock aim at arm

    elif _swing_armed:
        if hp_axis < _peak_axis_hp: _peak_axis_hp = hp_axis
        if hp_mag  < _peak_mag_hp:  _peak_mag_hp  = hp_mag

        near_base = (max(abs(hp_axis), abs(hp_mag)) <= SWING_END_THRESHOLD_G)
        timed_out = ((now_s - _swing_start_ts) > SWING_MAX_WINDOW_S)
        if near_base or timed_out:
            final_power = _angle_to_power(yaw_rel_deg())
            shoot = True
            _swing_armed = False
            _swing_start_ts = 0.0
            _peak_axis_hp = 0.0
            _peak_mag_hp = 0.0

    # Live preview follows current yaw angle (can go up or down)
    raw_preview = _angle_to_power(yaw_rel_deg())

    return shoot, raw_preview, final_power

# =========================
#        MAIN ENTRY
# =========================
def get_latest_shot_data(sensor_server):
    """
    Angle from integrated gyro rate on AIM_AXIS.
    Power from absolute yaw angle (gyroscope_absolute[POWER_YAW_AXIS]) relative to lazy baseline.
    Shot when accelerometer shows fast-down impulse that settles.

    Returns:
      {
        "angle": radians,
        "angle_deg": degrees,
        "power": 0..1,         # preview or final (snapped on shoot)
        "power_raw": 0..1,     # instantaneous preview
        "shoot": bool,
        "aim_locked": bool,    # True while downswing armed
        "angle_locked": radians  # aim angle captured at arm
      }
    """
    global _last_ts, _smoothed_power, _yaw_abs_deg, _yaw_zero_deg

    data = sensor_server.get_latest_data()
    now_s = time.time()
    dt = (now_s - _last_ts) if _last_ts is not None else 0.0
    _last_ts = now_s

    # -------- Simulator fallback --------
    if not data:
        pass
        # # simulate absolute yaw for POWER
        # _yaw_abs_deg = 30.0 * math.sin(now_s * 0.6)  # degrees
        # if _yaw_zero_deg is None:
        #     _yaw_zero_deg = _yaw_abs_deg
        # empty = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        # # simulate aim rate and accel arm/end
        # sim_rate_deg_s = 45.0 * math.sin(now_s * 0.6)
        # _integrate_aim(math.radians(sim_rate_deg_s) if GYRO_RATE_IS_RAD_PER_S else sim_rate_deg_s, empty, dt)

        # phase = (now_s % CONFIG.get('simulator_power_cycle_seconds', 3.0))
        # if phase < 0.12:
        #     hp_axis = SWING_DOWN_TRIG_AXIS_G - 0.05  # arm
        #     hp_mag = SWING_DOWN_TRIG_MAG_G - 0.05
        # elif 0.12 <= phase < 0.22:
        #     hp_axis = 0.0  # end
        #     hp_mag = 0.0
        # else:
        #     hp_axis = 0.0
        #     hp_mag = 0.0

        # shoot, raw_preview, final_power = _update_swing_detector(hp_axis, hp_mag, now_s)

        # if shoot and SNAP_POWER_ON_SHOOT:
        #     _smoothed_power = final_power
        # else:
        #     target = final_power if shoot else raw_preview
        #     _smoothed_power += POWER_SMOOTHING_ALPHA * (target - _smoothed_power)

        # return {
        #     "angle": math.radians(aim_angle_deg),
        #     "angle_deg": aim_angle_deg,
        #     "power": _clamp(_smoothed_power, 0.0, 1.0),
        #     "power_raw": _clamp(raw_preview, 0.0, 1.0),
        #     "shoot": shoot,
        #     "aim_locked": bool(_swing_armed),
        #     "angle_locked": math.radians(_aim_lock_deg)
        # }

    # -------- Real sensor path --------
    try:
        # Accelerometer
        accel = data.get('accelerometer')
        if not isinstance(accel, dict):
            raise KeyError("accelerometer")

        # Absolute yaw for POWER
        ga = data.get('gyroscope_absolute')
        #gna = pygame.math.Vector3(data.get('gyroscope')["x"], data.get('gyroscope')["y"], data.get('gyroscope')["z"])
         # back-compat
        if isinstance(ga, dict) and POWER_YAW_AXIS in ga:
            _yaw_abs_deg = float(ga[POWER_YAW_AXIS])
        else:
            # If missing, keep last value; do not crash
            pass

        # Lazy baseline for yaw
        if _yaw_zero_deg is None:
            _yaw_zero_deg = _yaw_abs_deg

        # Gyro rate for AIM
        gr = data.get('gyroscope_rate')
        if not isinstance(gr, dict):
            # Back-compat: some payloads might use 'gyroscope'
            gr = data.get('gyroscope')

        grvector = pygame.math.Vector3(gr["x"], gr["y"], gr["z"])
        gyro_rate_val = float(gr.get(AIM_AXIS, 0.0)) if isinstance(gr, dict) else 0.0
        gyro_dps_raw = _to_dps(gyro_rate_val)

        # Update baselines and bias; get high-pass signals from accel
        hp_axis, hp_mag = _update_bias_and_baselines(accel, gyro_dps_raw)

        print(grvector.magnitude())
        if grvector.magnitude() < 7:
            gyro_rate_val = 0
        # Integrate aim using bias-compensated rate
        _integrate_aim(gyro_rate_val, accel, dt if dt > 0 else 0.0)

        # Swing detector -> power from yaw angle only
        shoot, raw_preview, final_power = _update_swing_detector(hp_axis, hp_mag, now_s)

        # Power smoothing
        if shoot and SNAP_POWER_ON_SHOOT:
            _smoothed_power = final_power  # snap to peak at the trigger frame
        else:
            target = final_power if shoot else raw_preview
            _smoothed_power += POWER_SMOOTHING_ALPHA * (target - _smoothed_power)

        return {
            "angle": math.radians(aim_angle_deg),
            "angle_deg": aim_angle_deg,
            "power": _clamp(_smoothed_power, 0.0, 1.0),
            "power_raw": _clamp(raw_preview, 0.0, 1.0),
            "shoot": bool(shoot),
            "aim_locked": bool(_swing_armed),
            "angle_locked": math.radians(_aim_lock_deg)
        }

    except (KeyError, TypeError, ValueError):
        print("Warning: sensor data missing or invalid.")
        return {
            "angle": 0.0, "angle_deg": 0.0,
            "power": 0.0, "power_raw": 0.0,
            "shoot": False, "aim_locked": False, "angle_locked": 0.0
        }
