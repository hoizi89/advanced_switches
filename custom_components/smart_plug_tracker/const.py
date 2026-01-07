"""Constants for Smart Plug Tracker integration."""
from homeassistant.const import Platform

DOMAIN = "smart_plug_tracker"
PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR]

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

# States
STATE_OFF = "off"
STATE_STANDBY = "standby"
STATE_ACTIVE = "active"

# Attributes for persistence
ATTR_SESSIONS_TOTAL = "sessions_total"
ATTR_SESSIONS_TODAY = "sessions_today"
ATTR_ENERGY_TODAY_KWH = "energy_today_kwh"
ATTR_LAST_SESSION_DURATION_S = "last_session_duration_s"
ATTR_LAST_SESSION_ENERGY_KWH = "last_session_energy_kwh"
ATTR_TODAY_DATE = "today_date"
ATTR_SESSION_ACTIVE = "session_active"
ATTR_SESSION_START_TIME = "session_start_time"
ATTR_SESSION_START_ENERGY = "session_start_energy"
