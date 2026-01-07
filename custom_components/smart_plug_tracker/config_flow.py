"""Config flow for Smart Plug Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVE_THRESHOLD_W,
    CONF_DEVICE_NAME,
    CONF_ENERGY_ENTITY,
    CONF_MIN_ACTIVE_S,
    CONF_MIN_SESSION_S,
    CONF_MODE,
    CONF_OFF_DELAY_S,
    CONF_ON_DELAY_S,
    CONF_POWER_ENTITY,
    CONF_SESSION_END_GRACE_S,
    CONF_STANDBY_THRESHOLD_W,
    CONF_SWITCH_ENTITY,
    DEFAULT_ACTIVE_THRESHOLD_W,
    DEFAULT_ACTIVE_THRESHOLD_W_STANDBY,
    DEFAULT_MIN_ACTIVE_S,
    DEFAULT_MIN_SESSION_S,
    DEFAULT_OFF_DELAY_S,
    DEFAULT_ON_DELAY_S,
    DEFAULT_SESSION_END_GRACE_S,
    DEFAULT_STANDBY_THRESHOLD_W,
    DOMAIN,
    MODE_SIMPLE,
    MODE_STANDBY,
)

_LOGGER = logging.getLogger(__name__)


class SmartPlugTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Plug Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - basic configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that all required entities are provided
            if not user_input.get(CONF_SWITCH_ENTITY):
                errors[CONF_SWITCH_ENTITY] = "required"
            if not user_input.get(CONF_POWER_ENTITY):
                errors[CONF_POWER_ENTITY] = "required"
            if not user_input.get(CONF_ENERGY_ENTITY):
                errors[CONF_ENERGY_ENTITY] = "required"

            if not errors:
                self._data = user_input
                # Go to mode-specific parameters
                if user_input[CONF_MODE] == MODE_SIMPLE:
                    return await self.async_step_simple_params()
                else:
                    return await self.async_step_standby_params()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME): str,
                    vol.Required(CONF_SWITCH_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="switch")
                    ),
                    vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="power",
                        )
                    ),
                    vol.Required(CONF_ENERGY_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="energy",
                        )
                    ),
                    vol.Required(CONF_MODE, default=MODE_SIMPLE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MODE_SIMPLE,
                                    label="Simple (OFF/ACTIVE)",
                                ),
                                selector.SelectOptionDict(
                                    value=MODE_STANDBY,
                                    label="Standby (OFF/STANDBY/ACTIVE)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_simple_params(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle simple mode parameters."""
        if user_input is not None:
            self._data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="simple_params",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ACTIVE_THRESHOLD_W,
                        default=DEFAULT_ACTIVE_THRESHOLD_W,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=10000,
                            step=1,
                            unit_of_measurement="W",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ON_DELAY_S,
                        default=DEFAULT_ON_DELAY_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_OFF_DELAY_S,
                        default=DEFAULT_OFF_DELAY_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_MIN_ACTIVE_S,
                        default=DEFAULT_MIN_ACTIVE_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=600,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    async def async_step_standby_params(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle standby mode parameters."""
        if user_input is not None:
            self._data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="standby_params",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STANDBY_THRESHOLD_W,
                        default=DEFAULT_STANDBY_THRESHOLD_W,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=1000,
                            step=1,
                            unit_of_measurement="W",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ACTIVE_THRESHOLD_W,
                        default=DEFAULT_ACTIVE_THRESHOLD_W_STANDBY,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=10000,
                            step=1,
                            unit_of_measurement="W",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ON_DELAY_S,
                        default=DEFAULT_ON_DELAY_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_OFF_DELAY_S,
                        default=DEFAULT_OFF_DELAY_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_SESSION_END_GRACE_S,
                        default=DEFAULT_SESSION_END_GRACE_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=600,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_MIN_SESSION_S,
                        default=DEFAULT_MIN_SESSION_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=600,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._data[CONF_DEVICE_NAME],
            data=self._data,
        )
