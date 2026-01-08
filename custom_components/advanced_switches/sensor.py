"""Sensor platform for Advanced Switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvancedSwitchController
from .const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    STATE_ACTIVE,
    STATE_BLOCKED,
    STATE_OFF,
    STATE_STANDBY,
)

_LOGGER = logging.getLogger(__name__)


def format_duration(seconds: int | float | None) -> str:
    """Format seconds as human-readable duration (e.g., '1h 15m 30s')."""
    if seconds is None or seconds < 0:
        return ""

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    controller: AdvancedSwitchController = hass.data[DOMAIN][entry.entry_id]

    entities = [
        StateSensor(controller, entry),
        SessionsTotalSensor(controller, entry),
        SessionsTodaySensor(controller, entry),
        LastSessionDurationSensor(controller, entry),
        LastSessionEnergySensor(controller, entry),
        LastSessionPeakPowerSensor(controller, entry),
        EnergyTodaySensor(controller, entry),
        EnergyTotalSensor(controller, entry),
        # Live session sensors (diagnostic)
        CurrentSessionDurationSensor(controller, entry),
        CurrentSessionEnergySensor(controller, entry),
        CurrentSessionPeakPowerSensor(controller, entry),
        # Average sensors (diagnostic)
        AvgSessionDurationSensor(controller, entry),
        AvgSessionEnergySensor(controller, entry),
        # Smoothed power sensor (diagnostic)
        SmoothedPowerSensor(controller, entry),
    ]

    # Add auto-off sensors if auto-off is enabled
    if controller.auto_off_enabled:
        entities.append(AutoOffAtSensor(controller, entry))
        entities.append(AutoOffRemainingSensor(controller, entry))

    async_add_entities(entities)


class BaseEntity(SensorEntity):
    """Base class for Advanced Switches sensors."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self._ctrl = controller
        self._entry = entry

        # Link to source device if available, otherwise create virtual device
        source_identifiers = controller.get_source_device_identifiers()
        if source_identifiers:
            self._attr_device_info = DeviceInfo(
                identifiers=source_identifiers,
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=entry.data[CONF_DEVICE_NAME],
                manufacturer="Advanced Switches",
                model="Virtual Device",
            )

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        await super().async_added_to_hass()
        self._ctrl.register_entity_listener(self._on_controller_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        self._ctrl.unregister_entity_listener(self._on_controller_update)
        await super().async_will_remove_from_hass()

    @callback
    def _on_controller_update(self) -> None:
        """Handle controller updates."""
        self.async_write_ha_state()


class StateSensor(BaseEntity):
    """Sensor showing current state (off/standby/active/blocked)."""

    _attr_translation_key = "state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_OFF, STATE_STANDBY, STATE_ACTIVE, STATE_BLOCKED]

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"

    @property
    def native_value(self) -> str:
        """Return the current state."""
        return self._ctrl.state

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        icons = {
            STATE_OFF: "mdi:power-plug-off",
            STATE_STANDBY: "mdi:power-standby",
            STATE_ACTIVE: "mdi:power-plug",
            STATE_BLOCKED: "mdi:clock-alert-outline",
        }
        return icons.get(self._ctrl.state, "mdi:help")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        attrs = {
            "current_power_w": round(self._ctrl.current_power, 2),
            "smoothed_power_w": round(self._ctrl.smoothed_power, 2),
            "mode": self._ctrl.mode,
            "standby_threshold_w": round(self._ctrl._standby_threshold_w, 2),
            "active_threshold_w": round(self._ctrl._active_threshold_w, 2),
            "pending_session_end": self._ctrl._pending_session_end,
        }

        # Schedule info
        if self._ctrl.schedule_enabled:
            attrs["schedule_enabled"] = True
            attrs["schedule_start"] = str(self._ctrl.schedule_start)
            attrs["schedule_end"] = str(self._ctrl.schedule_end)
            attrs["schedule_blocked"] = self._ctrl.schedule_blocked
            attrs["schedule_turned_off"] = self._ctrl.schedule_turned_off

        # Auto-off info
        if self._ctrl.auto_off_enabled:
            attrs["auto_off_enabled"] = True
            attrs["auto_off_minutes"] = self._ctrl.auto_off_minutes

        return attrs


class SessionsTotalSensor(RestoreSensor, BaseEntity):
    """Sensor showing total session count."""

    _attr_translation_key = "sessions_total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_sessions_total"

    async def async_added_to_hass(self) -> None:
        """Restore state and register callbacks."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.attributes:
                self._ctrl.restore_state(last_state.attributes)

    @property
    def native_value(self) -> int:
        """Return the total session count."""
        return self._ctrl.sessions_total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return persistence attributes."""
        return self._ctrl.get_persistence_data()


class SessionsTodaySensor(BaseEntity):
    """Sensor showing today's session count."""

    _attr_translation_key = "sessions_today"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:counter"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_sessions_today"

    @property
    def native_value(self) -> int:
        """Return today's session count."""
        return self._ctrl.sessions_today


class LastSessionDurationSensor(BaseEntity):
    """Sensor showing last session duration."""

    _attr_translation_key = "last_session_duration"
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_session_duration"

    @property
    def native_value(self) -> str | None:
        """Return the last session duration formatted."""
        if self._ctrl.last_session_duration_s is None:
            return None
        return format_duration(self._ctrl.last_session_duration_s)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw seconds as attribute."""
        return {"seconds": self._ctrl.last_session_duration_s}


class LastSessionEnergySensor(BaseEntity):
    """Sensor showing last session energy consumption."""

    _attr_translation_key = "last_session_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_session_energy"

    @property
    def native_value(self) -> float | None:
        """Return the last session energy consumption."""
        return self._ctrl.last_session_energy_kwh


class LastSessionPeakPowerSensor(BaseEntity):
    """Sensor showing last session peak power."""

    _attr_translation_key = "last_session_peak_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:flash-triangle"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_session_peak_power"

    @property
    def native_value(self) -> float | None:
        """Return the last session peak power."""
        return self._ctrl.last_session_peak_power_w


class EnergyTodaySensor(BaseEntity):
    """Sensor showing today's energy consumption."""

    _attr_translation_key = "energy_today"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_energy_today"

    @property
    def native_value(self) -> float:
        """Return today's energy consumption."""
        return round(self._ctrl.energy_today_kwh, 3)


class EnergyTotalSensor(BaseEntity):
    """Sensor showing total energy consumption."""

    _attr_translation_key = "energy_total"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_energy_total"

    @property
    def native_value(self) -> float:
        """Return total energy consumption."""
        return round(self._ctrl.energy_total_kwh, 3)


# Live session sensors

class CurrentSessionDurationSensor(BaseEntity):
    """Sensor showing current session duration (live)."""

    _attr_translation_key = "current_session_duration"
    _attr_icon = "mdi:timer-play"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_session_duration"

    @property
    def native_value(self) -> str | None:
        """Return the current session duration formatted."""
        if self._ctrl.current_session_duration_s is None:
            return None
        return format_duration(self._ctrl.current_session_duration_s)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw seconds as attribute."""
        return {"seconds": self._ctrl.current_session_duration_s}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._ctrl.state in (STATE_STANDBY, STATE_ACTIVE)


class CurrentSessionEnergySensor(BaseEntity):
    """Sensor showing current session energy consumption (live)."""

    _attr_translation_key = "current_session_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_session_energy"

    @property
    def native_value(self) -> float | None:
        """Return the current session energy consumption."""
        value = self._ctrl.current_session_energy_kwh
        return round(value, 3) if value is not None else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._ctrl.state in (STATE_STANDBY, STATE_ACTIVE)


class CurrentSessionPeakPowerSensor(BaseEntity):
    """Sensor showing current session peak power (live)."""

    _attr_translation_key = "current_session_peak_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:flash-triangle-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_session_peak_power"

    @property
    def native_value(self) -> float | None:
        """Return the current session peak power."""
        if self._ctrl.state in (STATE_STANDBY, STATE_ACTIVE):
            return round(self._ctrl.session_peak_power, 1)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._ctrl.state in (STATE_STANDBY, STATE_ACTIVE)


# Average sensors

class AvgSessionDurationSensor(BaseEntity):
    """Sensor showing average session duration."""

    _attr_translation_key = "avg_session_duration"
    _attr_icon = "mdi:timer-sand"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_avg_session_duration"

    @property
    def native_value(self) -> str | None:
        """Return the average session duration formatted."""
        if self._ctrl.avg_session_duration_s is None:
            return None
        return format_duration(self._ctrl.avg_session_duration_s)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw seconds and session history as attributes."""
        return {
            "seconds": self._ctrl.avg_session_duration_s,
            "session_history": self._ctrl.session_history,
        }


class AvgSessionEnergySensor(BaseEntity):
    """Sensor showing average session energy consumption."""

    _attr_translation_key = "avg_session_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:chart-line"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_avg_session_energy"

    @property
    def native_value(self) -> float | None:
        """Return the average session energy consumption."""
        return self._ctrl.avg_session_energy_kwh


class AutoOffAtSensor(BaseEntity):
    """Sensor showing when auto-off will trigger."""

    _attr_translation_key = "auto_off_at"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-off"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_auto_off_at"

    @property
    def native_value(self):
        """Return when auto-off will trigger."""
        return self._ctrl.auto_off_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return remaining time as attribute."""
        auto_off_at = self._ctrl.auto_off_at
        if auto_off_at is None:
            return {"remaining": None, "remaining_minutes": None}

        from datetime import datetime
        now = datetime.now(auto_off_at.tzinfo) if auto_off_at.tzinfo else datetime.now()
        remaining = auto_off_at - now

        if remaining.total_seconds() <= 0:
            return {"remaining": "0s", "remaining_minutes": 0}

        total_minutes = int(remaining.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            formatted = f"in {hours}h {minutes}min"
        elif minutes > 0:
            formatted = f"in {minutes} min"
        else:
            secs = int(remaining.total_seconds())
            formatted = f"in {secs}s"

        return {
            "remaining": formatted,
            "remaining_minutes": total_minutes,
        }


class AutoOffRemainingSensor(BaseEntity):
    """Sensor showing remaining time until auto-off as countdown."""

    _attr_translation_key = "auto_off_remaining"
    _attr_icon = "mdi:timer-sand"
    _attr_should_poll = True  # Enable polling for countdown updates

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_auto_off_remaining"

    @property
    def suggested_object_id(self) -> str:
        """Return suggested object ID."""
        return f"{self._ctrl.device_name}_auto_off_remaining".lower().replace(" ", "_")

    @property
    def native_value(self) -> str:
        """Return remaining time as human-readable string."""
        auto_off_at = self._ctrl.auto_off_at
        if auto_off_at is None:
            return "Inaktiv"

        from datetime import datetime
        now = datetime.now(auto_off_at.tzinfo) if auto_off_at.tzinfo else datetime.now()
        remaining = auto_off_at - now

        if remaining.total_seconds() <= 0:
            return "0s"

        total_minutes = int(remaining.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"in {hours}h {minutes}min"
        elif minutes > 0:
            return f"in {minutes} min"
        else:
            secs = int(remaining.total_seconds())
            return f"in {secs}s"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional info."""
        attrs = {
            "configured_minutes": self._ctrl.auto_off_minutes,
        }

        auto_off_at = self._ctrl.auto_off_at
        if auto_off_at is None:
            attrs["remaining_minutes"] = None
            attrs["auto_off_at"] = None
            attrs["status"] = "Timer startet wenn Schalter eingeschaltet wird"
            return attrs

        from datetime import datetime
        now = datetime.now(auto_off_at.tzinfo) if auto_off_at.tzinfo else datetime.now()
        remaining = auto_off_at - now
        total_minutes = max(0, int(remaining.total_seconds() / 60))

        attrs["remaining_minutes"] = total_minutes
        attrs["auto_off_at"] = auto_off_at.isoformat()
        attrs["status"] = "Timer läuft"
        return attrs


class SmoothedPowerSensor(BaseEntity):
    """Sensor showing smoothed (averaged) power value."""

    _attr_translation_key = "smoothed_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-line-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_smoothed_power"

    @property
    def native_value(self) -> float:
        """Return the smoothed power value."""
        return round(self._ctrl.smoothed_power, 2)
