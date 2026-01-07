"""Advanced Switches integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_change

from .const import (
    ATTR_ENERGY_TODAY_KWH,
    ATTR_LAST_SESSION_DURATION_S,
    ATTR_LAST_SESSION_ENERGY_KWH,
    ATTR_SESSION_ACTIVE,
    ATTR_SESSION_START_ENERGY,
    ATTR_SESSION_START_TIME,
    ATTR_SESSIONS_TODAY,
    ATTR_SESSIONS_TOTAL,
    ATTR_TODAY_DATE,
    CONF_ACTIVE_THRESHOLD_W,
    CONF_DEVICE_NAME,
    CONF_ENERGY_ENTITY,
    CONF_MIN_ACTIVE_S,
    CONF_MIN_SESSION_S,
    CONF_MODE,
    CONF_OFF_DELAY_S,
    CONF_ON_DELAY_S,
    CONF_POWER_ENTITY,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_END,
    CONF_SCHEDULE_START,
    CONF_SESSION_END_GRACE_S,
    CONF_STANDBY_THRESHOLD_W,
    CONF_SWITCH_ENTITY,
    DEFAULT_ACTIVE_THRESHOLD_W,
    DEFAULT_ACTIVE_THRESHOLD_W_STANDBY,
    DEFAULT_MIN_ACTIVE_S,
    DEFAULT_MIN_SESSION_S,
    DEFAULT_OFF_DELAY_S,
    DEFAULT_ON_DELAY_S,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_SCHEDULE_ENABLED,
    DEFAULT_SCHEDULE_END,
    DEFAULT_SCHEDULE_START,
    DEFAULT_SESSION_END_GRACE_S,
    DEFAULT_STANDBY_THRESHOLD_W,
    DOMAIN,
    MODE_SIMPLE,
    MODE_STANDBY,
    PLATFORMS,
    STATE_ACTIVE,
    STATE_BLOCKED,
    STATE_OFF,
    STATE_STANDBY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Advanced Switches from a config entry."""
    controller = AdvancedSwitchController(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await controller.async_start()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    controller: AdvancedSwitchController = hass.data[DOMAIN][entry.entry_id]
    await controller.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AdvancedSwitchController:
    """Controller for Advanced Switches."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the controller."""
        self.hass = hass
        self.entry = entry

        # Configuration
        self._device_name: str = entry.data[CONF_DEVICE_NAME]
        self._switch_entity: str = entry.data[CONF_SWITCH_ENTITY]
        self._power_entity: str = entry.data[CONF_POWER_ENTITY]
        self._energy_entity: str = entry.data[CONF_ENERGY_ENTITY]
        self._mode: str = entry.data[CONF_MODE]

        # Schedule configuration
        self._schedule_enabled: bool = entry.data.get(
            CONF_SCHEDULE_ENABLED, DEFAULT_SCHEDULE_ENABLED
        )
        self._schedule_start: time = self._parse_time(
            entry.data.get(CONF_SCHEDULE_START, DEFAULT_SCHEDULE_START)
        )
        self._schedule_end: time = self._parse_time(
            entry.data.get(CONF_SCHEDULE_END, DEFAULT_SCHEDULE_END)
        )
        self._schedule_days: list[int] = entry.data.get(
            CONF_SCHEDULE_DAYS, DEFAULT_SCHEDULE_DAYS
        )

        # Load mode-specific parameters
        if self._mode == MODE_SIMPLE:
            self._active_threshold_w: float = entry.data.get(
                CONF_ACTIVE_THRESHOLD_W, DEFAULT_ACTIVE_THRESHOLD_W
            )
            self._on_delay_s: int = entry.data.get(CONF_ON_DELAY_S, DEFAULT_ON_DELAY_S)
            self._off_delay_s: int = entry.data.get(CONF_OFF_DELAY_S, DEFAULT_OFF_DELAY_S)
            self._min_duration_s: int = entry.data.get(CONF_MIN_ACTIVE_S, DEFAULT_MIN_ACTIVE_S)
            self._standby_threshold_w: float = 0
            self._session_end_grace_s: int = self._off_delay_s
        else:  # Standby mode
            self._standby_threshold_w: float = entry.data.get(
                CONF_STANDBY_THRESHOLD_W, DEFAULT_STANDBY_THRESHOLD_W
            )
            self._active_threshold_w: float = entry.data.get(
                CONF_ACTIVE_THRESHOLD_W, DEFAULT_ACTIVE_THRESHOLD_W_STANDBY
            )
            self._on_delay_s: int = entry.data.get(CONF_ON_DELAY_S, DEFAULT_ON_DELAY_S)
            self._off_delay_s: int = entry.data.get(CONF_OFF_DELAY_S, DEFAULT_OFF_DELAY_S)
            self._session_end_grace_s: int = entry.data.get(
                CONF_SESSION_END_GRACE_S, DEFAULT_SESSION_END_GRACE_S
            )
            self._min_duration_s: int = entry.data.get(CONF_MIN_SESSION_S, DEFAULT_MIN_SESSION_S)

        # Current state
        self._state: str = STATE_OFF
        self._session_start_time: datetime | None = None
        self._session_start_energy: float | None = None
        self._current_energy: float | None = None
        self._power_available: bool = True
        self._energy_available: bool = True
        self._schedule_blocked: bool = False

        # Timers
        self._pending_on_timer: Any | None = None
        self._pending_off_timer: Any | None = None
        self._pending_target_state: str | None = None

        # Persistent statistics
        self._sessions_total: int = 0
        self._sessions_today: int = 0
        self._energy_today_kwh: float = 0.0
        self._last_session_duration_s: int | None = None
        self._last_session_energy_kwh: float | None = None
        self._today_date: date = date.today()
        self._state_restored: bool = False

        # Entity update listeners
        self._entity_listeners: list[Callable[[], None]] = []
        self._remove_listeners: list[Callable[[], None]] = []

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse time string to time object."""
        try:
            parts = time_str.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return time(6, 0)

    @property
    def device_name(self) -> str:
        """Return the device name."""
        return self._device_name

    @property
    def mode(self) -> str:
        """Return the operating mode."""
        return self._mode

    @property
    def state(self) -> str:
        """Return the current state."""
        if self._schedule_blocked:
            return STATE_BLOCKED
        return self._state

    @property
    def switch_entity(self) -> str:
        """Return the switch entity ID."""
        return self._switch_entity

    @property
    def sessions_total(self) -> int:
        """Return total sessions count."""
        return self._sessions_total

    @property
    def sessions_today(self) -> int:
        """Return today's sessions count."""
        return self._sessions_today

    @property
    def energy_today_kwh(self) -> float:
        """Return today's energy consumption."""
        return self._energy_today_kwh

    @property
    def last_session_duration_s(self) -> int | None:
        """Return last session duration in seconds."""
        return self._last_session_duration_s

    @property
    def last_session_energy_kwh(self) -> float | None:
        """Return last session energy consumption."""
        return self._last_session_energy_kwh

    @property
    def schedule_enabled(self) -> bool:
        """Return if schedule is enabled."""
        return self._schedule_enabled

    @property
    def schedule_blocked(self) -> bool:
        """Return if currently blocked by schedule."""
        return self._schedule_blocked

    @property
    def schedule_start(self) -> time:
        """Return schedule start time."""
        return self._schedule_start

    @property
    def schedule_end(self) -> time:
        """Return schedule end time."""
        return self._schedule_end

    @property
    def schedule_days(self) -> list[int]:
        """Return schedule days."""
        return self._schedule_days

    def _is_within_schedule(self) -> bool:
        """Check if current time is within the allowed schedule."""
        if not self._schedule_enabled:
            return True

        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()

        # Check if today is an allowed day
        if current_day not in self._schedule_days:
            return False

        # Check if current time is within range
        if self._schedule_start <= self._schedule_end:
            # Normal range (e.g., 06:00 - 22:00)
            return self._schedule_start <= current_time <= self._schedule_end
        else:
            # Overnight range (e.g., 22:00 - 06:00)
            return current_time >= self._schedule_start or current_time <= self._schedule_end

    async def _enforce_schedule(self) -> None:
        """Enforce the schedule by turning off switch if outside allowed time."""
        was_blocked = self._schedule_blocked
        self._schedule_blocked = not self._is_within_schedule()

        if self._schedule_blocked and not was_blocked:
            # Just entered blocked period
            _LOGGER.info(
                "%s: Outside schedule, turning off",
                self._device_name,
            )
            # Turn off the real switch
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self._switch_entity},
                blocking=True,
            )
            # End any active session
            if self._state != STATE_OFF:
                self._end_session()
            self._notify_entities()

        elif not self._schedule_blocked and was_blocked:
            # Just entered allowed period
            _LOGGER.info(
                "%s: Within schedule, switch enabled",
                self._device_name,
            )
            self._notify_entities()

    def register_entity_listener(self, callback_fn: Callable[[], None]) -> None:
        """Register a callback for entity updates."""
        self._entity_listeners.append(callback_fn)

    def unregister_entity_listener(self, callback_fn: Callable[[], None]) -> None:
        """Unregister a callback."""
        if callback_fn in self._entity_listeners:
            self._entity_listeners.remove(callback_fn)

    def restore_state(self, data: dict[str, Any]) -> None:
        """Restore state from persistent storage."""
        if self._state_restored:
            return

        self._sessions_total = int(data.get(ATTR_SESSIONS_TOTAL, 0))
        self._sessions_today = int(data.get(ATTR_SESSIONS_TODAY, 0))
        self._energy_today_kwh = float(data.get(ATTR_ENERGY_TODAY_KWH, 0.0))

        if data.get(ATTR_LAST_SESSION_DURATION_S) is not None:
            self._last_session_duration_s = int(data[ATTR_LAST_SESSION_DURATION_S])
        if data.get(ATTR_LAST_SESSION_ENERGY_KWH) is not None:
            self._last_session_energy_kwh = float(data[ATTR_LAST_SESSION_ENERGY_KWH])

        if data.get(ATTR_TODAY_DATE):
            try:
                self._today_date = date.fromisoformat(data[ATTR_TODAY_DATE])
            except (ValueError, TypeError):
                self._today_date = date.today()

        if data.get(ATTR_SESSION_ACTIVE):
            if data.get(ATTR_SESSION_START_TIME):
                try:
                    self._session_start_time = datetime.fromisoformat(
                        data[ATTR_SESSION_START_TIME]
                    )
                except (ValueError, TypeError):
                    self._session_start_time = None

            if data.get(ATTR_SESSION_START_ENERGY) is not None:
                self._session_start_energy = float(data[ATTR_SESSION_START_ENERGY])

            _LOGGER.debug(
                "Restored active session for %s, started at %s",
                self._device_name,
                self._session_start_time,
            )

        self._state_restored = True
        _LOGGER.debug(
            "Restored state for %s: total=%d, today=%d, energy_today=%.3f",
            self._device_name,
            self._sessions_total,
            self._sessions_today,
            self._energy_today_kwh,
        )

    def get_persistence_data(self) -> dict[str, Any]:
        """Get data for persistence."""
        return {
            ATTR_SESSIONS_TOTAL: self._sessions_total,
            ATTR_SESSIONS_TODAY: self._sessions_today,
            ATTR_ENERGY_TODAY_KWH: round(self._energy_today_kwh, 3),
            ATTR_LAST_SESSION_DURATION_S: self._last_session_duration_s,
            ATTR_LAST_SESSION_ENERGY_KWH: self._last_session_energy_kwh,
            ATTR_TODAY_DATE: self._today_date.isoformat(),
            ATTR_SESSION_ACTIVE: self._state != STATE_OFF,
            ATTR_SESSION_START_TIME: (
                self._session_start_time.isoformat() if self._session_start_time else None
            ),
            ATTR_SESSION_START_ENERGY: self._session_start_energy,
        }

    async def async_start(self) -> None:
        """Start the controller."""
        self._check_day_reset()

        # Initial schedule check
        await self._enforce_schedule()

        # Load initial energy value
        energy_state = self.hass.states.get(self._energy_entity)
        if energy_state and energy_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._current_energy = float(energy_state.state)
            except ValueError:
                pass

        # Check current power
        if not self._schedule_blocked:
            power_state = self.hass.states.get(self._power_entity)
            if power_state and power_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    power = float(power_state.state)
                    await self._handle_power_change(power, initial=True)
                except ValueError:
                    pass

        # Register state change listener
        @callback
        def state_listener(event: Event) -> None:
            """Handle state changes."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            self.hass.async_create_task(self._on_state_changed(entity_id, new_state))

        self._remove_listeners.append(
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, state_listener)
        )

        # Register schedule check every minute if schedule is enabled
        if self._schedule_enabled:
            @callback
            def schedule_check(_: datetime) -> None:
                """Check schedule every minute."""
                self.hass.async_create_task(self._enforce_schedule())

            self._remove_listeners.append(
                async_track_time_change(self.hass, schedule_check, second=0)
            )

        _LOGGER.info("Advanced Switches started for %s", self._device_name)

    async def async_stop(self) -> None:
        """Stop the controller."""
        self._cancel_on_timer()
        self._cancel_off_timer()

        for remove_listener in self._remove_listeners:
            remove_listener()
        self._remove_listeners.clear()

        _LOGGER.info("Advanced Switches stopped for %s", self._device_name)

    async def _on_state_changed(self, entity_id: str, new_state: Any) -> None:
        """Handle state changes from monitored entities."""
        if new_state is None:
            return

        if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            if entity_id == self._power_entity:
                self._power_available = False
            elif entity_id == self._energy_entity:
                self._energy_available = False
            return

        if entity_id == self._power_entity:
            self._power_available = True
            try:
                power = float(new_state.state)
                await self._handle_power_change(power)
            except ValueError:
                _LOGGER.debug("Invalid power value: %s", new_state.state)

        elif entity_id == self._energy_entity:
            self._energy_available = True
            try:
                self._current_energy = float(new_state.state)
            except ValueError:
                _LOGGER.debug("Invalid energy value: %s", new_state.state)

    async def _handle_power_change(self, power: float, initial: bool = False) -> None:
        """Handle power value changes."""
        # Don't process if blocked by schedule
        if self._schedule_blocked:
            return

        self._check_day_reset()

        if self._mode == MODE_SIMPLE:
            await self._handle_simple_mode(power, initial)
        else:
            await self._handle_standby_mode(power, initial)

    async def _handle_simple_mode(self, power: float, initial: bool = False) -> None:
        """Handle power changes in simple mode (OFF/ACTIVE only)."""
        if self._state == STATE_OFF:
            if power >= self._active_threshold_w:
                if initial:
                    self._transition_to(STATE_ACTIVE)
                else:
                    self._start_on_timer(STATE_ACTIVE)
            else:
                self._cancel_on_timer()

        elif self._state == STATE_ACTIVE:
            if power < self._active_threshold_w:
                self._start_off_timer()
            else:
                self._cancel_off_timer()

    async def _handle_standby_mode(self, power: float, initial: bool = False) -> None:
        """Handle power changes in standby mode (OFF/STANDBY/ACTIVE)."""
        if self._state == STATE_OFF:
            if power >= self._active_threshold_w:
                if initial:
                    self._transition_to(STATE_ACTIVE)
                else:
                    self._start_on_timer(STATE_ACTIVE)
            elif power >= self._standby_threshold_w:
                if initial:
                    self._transition_to(STATE_STANDBY)
                else:
                    self._start_on_timer(STATE_STANDBY)
            else:
                self._cancel_on_timer()

        elif self._state == STATE_STANDBY:
            if power >= self._active_threshold_w:
                self._cancel_off_timer()
                self._transition_to(STATE_ACTIVE)
            elif power < self._standby_threshold_w:
                self._start_off_timer(use_grace=True)
            else:
                self._cancel_off_timer()

        elif self._state == STATE_ACTIVE:
            if power < self._standby_threshold_w:
                self._start_off_timer(use_grace=True)
            elif power < self._active_threshold_w:
                self._cancel_off_timer()
                self._transition_to(STATE_STANDBY)
            else:
                self._cancel_off_timer()

    def _start_on_timer(self, target_state: str) -> None:
        """Start timer for state transition to on/active."""
        if self._pending_on_timer is not None:
            if self._pending_target_state == target_state:
                return
            self._cancel_on_timer()

        self._pending_target_state = target_state

        @callback
        def on_timer_callback(_: datetime) -> None:
            """Handle on timer expiration."""
            self._pending_on_timer = None
            self._pending_target_state = None
            self._transition_to(target_state)

        self._pending_on_timer = async_call_later(
            self.hass, self._on_delay_s, on_timer_callback
        )

    def _cancel_on_timer(self) -> None:
        """Cancel pending on timer."""
        if self._pending_on_timer is not None:
            self._pending_on_timer()
            self._pending_on_timer = None
            self._pending_target_state = None

    def _start_off_timer(self, use_grace: bool = False) -> None:
        """Start timer for state transition to off."""
        if self._pending_off_timer is not None:
            return

        delay = self._session_end_grace_s if use_grace else self._off_delay_s

        @callback
        def off_timer_callback(_: datetime) -> None:
            """Handle off timer expiration."""
            self._pending_off_timer = None
            self._end_session()

        self._pending_off_timer = async_call_later(self.hass, delay, off_timer_callback)

    def _cancel_off_timer(self) -> None:
        """Cancel pending off timer."""
        if self._pending_off_timer is not None:
            self._pending_off_timer()
            self._pending_off_timer = None

    def _transition_to(self, new_state: str) -> None:
        """Transition to a new state."""
        old_state = self._state

        if new_state == old_state:
            return

        if old_state == STATE_OFF and new_state in (STATE_STANDBY, STATE_ACTIVE):
            self._start_session()

        self._state = new_state
        _LOGGER.debug(
            "%s: State transition %s -> %s",
            self._device_name,
            old_state,
            new_state,
        )
        self._notify_entities()

    def _start_session(self) -> None:
        """Start a new session."""
        self._session_start_time = datetime.now()
        self._session_start_energy = self._current_energy
        _LOGGER.debug(
            "%s: Session started at %s with energy %.3f kWh",
            self._device_name,
            self._session_start_time,
            self._session_start_energy or 0,
        )

    def _end_session(self) -> None:
        """End the current session."""
        if self._session_start_time is None:
            self._state = STATE_OFF
            self._notify_entities()
            return

        now = datetime.now()
        duration_s = (now - self._session_start_time).total_seconds()

        if duration_s < self._min_duration_s:
            _LOGGER.debug(
                "%s: Session discarded (duration %.1fs < min %ds)",
                self._device_name,
                duration_s,
                self._min_duration_s,
            )
            self._reset_session()
            return

        if self._current_energy is not None and self._session_start_energy is not None:
            energy_kwh = max(0.0, self._current_energy - self._session_start_energy)
        else:
            energy_kwh = 0.0
            _LOGGER.debug("%s: Energy sensor unavailable, session energy set to 0", self._device_name)

        self._sessions_total += 1
        self._sessions_today += 1
        self._energy_today_kwh += energy_kwh
        self._last_session_duration_s = int(duration_s)
        self._last_session_energy_kwh = round(energy_kwh, 3)

        _LOGGER.info(
            "%s: Session ended - duration: %ds, energy: %.3f kWh",
            self._device_name,
            self._last_session_duration_s,
            self._last_session_energy_kwh,
        )

        self._reset_session()

    def _reset_session(self) -> None:
        """Reset session state."""
        self._session_start_time = None
        self._session_start_energy = None
        self._state = STATE_OFF
        self._notify_entities()

    def _check_day_reset(self) -> None:
        """Check if we need to reset daily counters."""
        today = date.today()
        if self._today_date != today:
            _LOGGER.debug(
                "%s: Day changed, resetting daily counters",
                self._device_name,
            )
            self._sessions_today = 0
            self._energy_today_kwh = 0.0
            self._today_date = today
            self._notify_entities()

    def _notify_entities(self) -> None:
        """Notify all registered entities of updates."""
        for callback_fn in self._entity_listeners:
            try:
                callback_fn()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error notifying entity listener")

    async def async_can_turn_on(self) -> bool:
        """Check if the switch can be turned on (respects schedule)."""
        return not self._schedule_blocked
