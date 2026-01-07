"""Switch platform for Advanced Switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
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
    """Set up switch entities."""
    controller: AdvancedSwitchController = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([ProxySwitch(controller, entry)])


class ProxySwitch(SwitchEntity):
    """Proxy switch that controls the real smart plug with schedule support."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "power"
    _attr_icon = "mdi:power-plug"

    def __init__(
        self,
        controller: AdvancedSwitchController,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        self._ctrl = controller
        self._entry = entry
        self._real_switch = controller.switch_entity
        self._attr_unique_id = f"{entry.entry_id}_power"

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

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        state = self.hass.states.get(self._real_switch)
        if state is None:
            return None
        return state.state == STATE_ON

    @property
    def available(self) -> bool:
        """Return if the switch is available (not blocked by schedule)."""
        return not self._ctrl.schedule_blocked

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (if allowed by schedule)."""
        if self._ctrl.schedule_blocked:
            _LOGGER.warning(
                "%s: Cannot turn on - outside allowed schedule",
                self._ctrl.device_name,
            )
            return

        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": self._real_switch},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": self._real_switch},
            blocking=True,
        )

    async def async_added_to_hass(self) -> None:
        """Register state change listener."""
        await super().async_added_to_hass()

        # Listen for real switch changes
        @callback
        def state_listener(event) -> None:
            """Handle state changes of the real switch."""
            if event.data.get("entity_id") == self._real_switch:
                self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen("state_changed", state_listener)
        )

        # Listen for controller updates (schedule changes)
        self._ctrl.register_entity_listener(self._on_controller_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        self._ctrl.unregister_entity_listener(self._on_controller_update)
        await super().async_will_remove_from_hass()

    @callback
    def _on_controller_update(self) -> None:
        """Handle controller updates."""
        self.async_write_ha_state()
