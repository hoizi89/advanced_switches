"""Binary sensor platform for Advanced Switches."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvancedSwitchController
from .const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    MODE_STANDBY,
    STATE_ACTIVE,
    STATE_STANDBY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    controller: AdvancedSwitchController = hass.data[DOMAIN][entry.entry_id]

    entities = [ActiveBinarySensor(controller, entry)]

    # Only add "on" sensor for standby mode
    if controller.mode == MODE_STANDBY:
        entities.append(OnBinarySensor(controller, entry))

    # Add schedule blocked sensor if schedule is enabled
    if controller.schedule_enabled:
        entities.append(ScheduleBlockedSensor(controller, entry))

    async_add_entities(entities)


class BaseBinarySensor(BinarySensorEntity):
    """Base class for binary sensors."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
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


class ActiveBinarySensor(BaseBinarySensor):
    """Binary sensor showing if device is actively running."""

    _attr_translation_key = "active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_active"

    @property
    def is_on(self) -> bool:
        """Return true if device is in active state."""
        return self._ctrl.state == STATE_ACTIVE


class OnBinarySensor(BaseBinarySensor):
    """Binary sensor showing if device is on (standby or active)."""

    _attr_translation_key = "on"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_on"

    @property
    def is_on(self) -> bool:
        """Return true if device is in standby or active state."""
        return self._ctrl.state in (STATE_STANDBY, STATE_ACTIVE)


class ScheduleBlockedSensor(BaseBinarySensor):
    """Binary sensor showing if device is blocked by schedule."""

    _attr_translation_key = "schedule_blocked"
    _attr_device_class = BinarySensorDeviceClass.LOCK

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_schedule_blocked"

    @property
    def is_on(self) -> bool:
        """Return true if device is blocked by schedule."""
        return self._ctrl.schedule_blocked
