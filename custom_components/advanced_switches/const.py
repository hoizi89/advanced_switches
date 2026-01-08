"""Constants for Advanced Switches integration."""
from homeassistant.const import Platform

DOMAIN = "advanced_switches"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Config keys
CONF_DEVICE_NAME = "device_name"
CONF_SWITCH_ENTITY = "switch_entity"
CONF_POWER_ENTITY = "power_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_MODE = "mode"

# Mode options
MODE_SIMPLE = "simple"
MODE_STANDBY = "standby"

# Simple mode parameters
CONF_ACTIVE_THRESHOLD_W = "active_threshold_w"
CONF_ON_DELAY_S = "on_delay_s"
CONF_OFF_DELAY_S = "off_delay_s"
CONF_MIN_ACTIVE_S = "min_active_s"

# Standby mode parameters
CONF_STANDBY_THRESHOLD_W = "standby_threshold_w"
CONF_SESSION_END_GRACE_S = "session_end_grace_s"
CONF_MIN_SESSION_S = "min_session_s"
CONF_ACTIVE_STANDBY_DELAY_S = "active_standby_delay_s"
CONF_POWER_SMOOTHING_S = "power_smoothing_s"
CONF_SESSION_END_ON_STANDBY = "session_end_on_standby"

# Schedule parameters
CONF_SCHEDULE_ENABLED = "schedule_enabled"
CONF_SCHEDULE_START = "schedule_start"
CONF_SCHEDULE_END = "schedule_end"
CONF_SCHEDULE_DAYS = "schedule_days"

# Auto-off timer
CONF_AUTO_OFF_ENABLED = "auto_off_enabled"
CONF_AUTO_OFF_MINUTES = "auto_off_minutes"

# Defaults - Simple mode
DEFAULT_ACTIVE_THRESHOLD_W = 50
DEFAULT_ON_DELAY_S = 3
DEFAULT_OFF_DELAY_S = 5
DEFAULT_MIN_ACTIVE_S = 10

# Defaults - Standby mode
DEFAULT_STANDBY_THRESHOLD_W = 5
DEFAULT_ACTIVE_THRESHOLD_W_STANDBY = 1000
DEFAULT_SESSION_END_GRACE_S = 120
DEFAULT_MIN_SESSION_S = 60
DEFAULT_ACTIVE_STANDBY_DELAY_S = 30
DEFAULT_POWER_SMOOTHING_S = 0
DEFAULT_SESSION_END_ON_STANDBY = False  # False=Sauna (Ende bei OFF), True=Waschmaschine (Ende bei STANDBY)

# Defaults - Schedule
DEFAULT_SCHEDULE_ENABLED = False
DEFAULT_SCHEDULE_START = "06:00"
DEFAULT_SCHEDULE_END = "22:00"
DEFAULT_SCHEDULE_DAYS = [0, 1, 2, 3, 4, 5, 6]  # All days (Mon=0, Sun=6)

# Defaults - Auto-off timer
DEFAULT_AUTO_OFF_ENABLED = False
DEFAULT_AUTO_OFF_MINUTES = 60

# Session history
SESSION_HISTORY_SIZE = 10

# States
STATE_OFF = "off"
STATE_STANDBY = "standby"
STATE_ACTIVE = "active"
STATE_BLOCKED = "blocked"  # Outside schedule

# Attributes for persistence
ATTR_SESSIONS_TOTAL = "sessions_total"
ATTR_SESSIONS_TODAY = "sessions_today"
ATTR_ENERGY_TODAY_KWH = "energy_today_kwh"
ATTR_LAST_SESSION_DURATION_S = "last_session_duration_s"
ATTR_LAST_SESSION_ENERGY_KWH = "last_session_energy_kwh"
ATTR_LAST_SESSION_PEAK_POWER_W = "last_session_peak_power_w"
ATTR_TODAY_DATE = "today_date"
ATTR_SESSION_ACTIVE = "session_active"
ATTR_SESSION_START_TIME = "session_start_time"
ATTR_SESSION_START_ENERGY = "session_start_energy"
ATTR_SESSION_PEAK_POWER = "session_peak_power"
ATTR_SESSION_HISTORY = "session_history"
ATTR_AVG_SESSION_DURATION_S = "avg_session_duration_s"
ATTR_AVG_SESSION_ENERGY_KWH = "avg_session_energy_kwh"
ATTR_ENERGY_TOTAL_KWH = "energy_total_kwh"
