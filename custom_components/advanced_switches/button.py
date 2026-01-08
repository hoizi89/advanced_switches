"""Button platform for Advanced Switches."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvancedSwitchController
from .const import CONF_DEVICE_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    controller: AdvancedSwitchController = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ResetAllCountersButton(controller, entry),
        ResetTodayCountersButton(controller, entry),
    ]

    async_add_entities(entities)


class BaseButton(ButtonEntity):
    """Base class for Advanced Switches buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
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


class ResetAllCountersButton(BaseButton):
    """Button to reset all counters."""

    _attr_translation_key = "reset_all_counters"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_reset_all_counters"

    async def async_press(self) -> None:
        """Handle the button press."""
        self._ctrl.reset_all_counters()


class ResetTodayCountersButton(BaseButton):
    """Button to reset today's counters."""

    _attr_translation_key = "reset_today_counters"
    _attr_icon = "mdi:calendar-refresh"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(controller, entry)
        self._attr_unique_id = f"{entry.entry_id}_reset_today_counters"

    async def async_press(self) -> None:
        """Handle the button press."""
        self._ctrl.reset_today_counters()
