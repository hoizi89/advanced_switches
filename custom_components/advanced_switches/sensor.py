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
        # Live session sensors
        CurrentSessionDurationSensor(controller, entry),
        CurrentSessionEnergySensor(controller, entry),
        CurrentSessionPeakPowerSensor(controller, entry),
        # Average sensors
        AvgSessionDurationSensor(controller, entry),
        AvgSessionEnergySensor(controller, entry),
    ]

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
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
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
    def native_value(self) -> int | None:
        """Return the last session duration in seconds."""
        return self._ctrl.last_session_duration_s


class LastSessionEnergySensor(BaseEntity):
    """Sensor showing last session energy consumption."""

    _attr_translation_key = "last_session_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
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


# Live session sensors

class CurrentSessionDurationSensor(BaseEntity):
    """Sensor showing current session duration (live)."""

    _attr_translation_key = "current_session_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-play"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_session_duration"

    @property
    def native_value(self) -> int | None:
        """Return the current session duration in seconds."""
        return self._ctrl.current_session_duration_s

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
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
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
    def native_value(self) -> float | None:
        """Return the average session duration."""
        return self._ctrl.avg_session_duration_s

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return session history as attributes."""
        return {"session_history": self._ctrl.session_history}


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
