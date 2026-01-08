"""Config flow for Advanced Switches integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVE_STANDBY_DELAY_S,
    CONF_ACTIVE_THRESHOLD_W,
    CONF_AUTO_OFF_ENABLED,
    CONF_AUTO_OFF_MINUTES,
    CONF_DEVICE_NAME,
    CONF_ENERGY_ENTITY,
    CONF_MIN_ACTIVE_S,
    CONF_MIN_SESSION_S,
    CONF_MODE,
    CONF_OFF_DELAY_S,
    CONF_ON_DELAY_S,
    CONF_POWER_ENTITY,
    CONF_POWER_SMOOTHING_S,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_END,
    CONF_SCHEDULE_START,
    CONF_SESSION_END_GRACE_S,
    CONF_STANDBY_THRESHOLD_W,
    CONF_SWITCH_ENTITY,
    DEFAULT_ACTIVE_STANDBY_DELAY_S,
    DEFAULT_ACTIVE_THRESHOLD_W,
    DEFAULT_ACTIVE_THRESHOLD_W_STANDBY,
    DEFAULT_AUTO_OFF_ENABLED,
    DEFAULT_AUTO_OFF_MINUTES,
    DEFAULT_MIN_ACTIVE_S,
    DEFAULT_MIN_SESSION_S,
    DEFAULT_OFF_DELAY_S,
    DEFAULT_ON_DELAY_S,
    DEFAULT_POWER_SMOOTHING_S,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_SCHEDULE_ENABLED,
    DEFAULT_SCHEDULE_END,
    DEFAULT_SCHEDULE_START,
    DEFAULT_SESSION_END_GRACE_S,
    DEFAULT_STANDBY_THRESHOLD_W,
    DOMAIN,
    MODE_SIMPLE,
    MODE_STANDBY,
)

_LOGGER = logging.getLogger(__name__)

WEEKDAYS = [
    {"value": "0", "label": "Montag"},
    {"value": "1", "label": "Dienstag"},
    {"value": "2", "label": "Mittwoch"},
    {"value": "3", "label": "Donnerstag"},
    {"value": "4", "label": "Freitag"},
    {"value": "5", "label": "Samstag"},
    {"value": "6", "label": "Sonntag"},
]


class AdvancedSwitchesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Advanced Switches."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return AdvancedSwitchesOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - basic configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_SWITCH_ENTITY):
                errors[CONF_SWITCH_ENTITY] = "required"
            if not user_input.get(CONF_POWER_ENTITY):
                errors[CONF_POWER_ENTITY] = "required"
            if not user_input.get(CONF_ENERGY_ENTITY):
                errors[CONF_ENERGY_ENTITY] = "required"

            if not errors:
                self._data = user_input
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
            return await self.async_step_schedule()

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
                    vol.Required(
                        CONF_POWER_SMOOTHING_S,
                        default=DEFAULT_POWER_SMOOTHING_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
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
            return await self.async_step_schedule()

        return self.async_show_form(
            step_id="standby_params",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STANDBY_THRESHOLD_W,
                        default=DEFAULT_STANDBY_THRESHOLD_W,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.1,
                            max=1000,
                            step=0.1,
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
                        CONF_ACTIVE_STANDBY_DELAY_S,
                        default=DEFAULT_ACTIVE_STANDBY_DELAY_S,
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
                    vol.Required(
                        CONF_POWER_SMOOTHING_S,
                        default=DEFAULT_POWER_SMOOTHING_S,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle schedule configuration."""
        if user_input is not None:
            # Convert day strings back to integers
            if CONF_SCHEDULE_DAYS in user_input:
                user_input[CONF_SCHEDULE_DAYS] = [
                    int(d) for d in user_input[CONF_SCHEDULE_DAYS]
                ]
            self._data.update(user_input)
            return self._create_entry()

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCHEDULE_ENABLED,
                        default=DEFAULT_SCHEDULE_ENABLED,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_SCHEDULE_START,
                        default=DEFAULT_SCHEDULE_START,
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_SCHEDULE_END,
                        default=DEFAULT_SCHEDULE_END,
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_SCHEDULE_DAYS,
                        default=[str(d) for d in DEFAULT_SCHEDULE_DAYS],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=d["value"], label=d["label"])
                                for d in WEEKDAYS
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
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


class AdvancedSwitchesOptionsFlow(OptionsFlow):
    """Handle options flow for Advanced Switches."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options - show menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["thresholds", "timing", "schedule", "auto_off", "reset"],
        )

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle threshold options."""
        if user_input is not None:
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current = self._config_entry.data
        mode = current.get(CONF_MODE, MODE_SIMPLE)

        if mode == MODE_SIMPLE:
            return self.async_show_form(
                step_id="thresholds",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_ACTIVE_THRESHOLD_W,
                            default=current.get(CONF_ACTIVE_THRESHOLD_W, DEFAULT_ACTIVE_THRESHOLD_W),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=1,
                                max=10000,
                                step=1,
                                unit_of_measurement="W",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
            )
        else:
            return self.async_show_form(
                step_id="thresholds",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_STANDBY_THRESHOLD_W,
                            default=current.get(CONF_STANDBY_THRESHOLD_W, DEFAULT_STANDBY_THRESHOLD_W),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.1,
                                max=1000,
                                step=0.1,
                                unit_of_measurement="W",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_ACTIVE_THRESHOLD_W,
                            default=current.get(CONF_ACTIVE_THRESHOLD_W, DEFAULT_ACTIVE_THRESHOLD_W_STANDBY),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=1,
                                max=10000,
                                step=1,
                                unit_of_measurement="W",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
            )

    async def async_step_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle timing options."""
        if user_input is not None:
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current = self._config_entry.data
        mode = current.get(CONF_MODE, MODE_SIMPLE)

        if mode == MODE_SIMPLE:
            return self.async_show_form(
                step_id="timing",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_ON_DELAY_S,
                            default=current.get(CONF_ON_DELAY_S, DEFAULT_ON_DELAY_S),
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
                            default=current.get(CONF_OFF_DELAY_S, DEFAULT_OFF_DELAY_S),
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
                            default=current.get(CONF_MIN_ACTIVE_S, DEFAULT_MIN_ACTIVE_S),
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
                            CONF_POWER_SMOOTHING_S,
                            default=current.get(CONF_POWER_SMOOTHING_S, DEFAULT_POWER_SMOOTHING_S),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0,
                                max=300,
                                step=1,
                                unit_of_measurement="s",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
            )
        else:
            return self.async_show_form(
                step_id="timing",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_ON_DELAY_S,
                            default=current.get(CONF_ON_DELAY_S, DEFAULT_ON_DELAY_S),
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
                            CONF_ACTIVE_STANDBY_DELAY_S,
                            default=current.get(CONF_ACTIVE_STANDBY_DELAY_S, DEFAULT_ACTIVE_STANDBY_DELAY_S),
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
                            default=current.get(CONF_SESSION_END_GRACE_S, DEFAULT_SESSION_END_GRACE_S),
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
                            default=current.get(CONF_MIN_SESSION_S, DEFAULT_MIN_SESSION_S),
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
                            CONF_POWER_SMOOTHING_S,
                            default=current.get(CONF_POWER_SMOOTHING_S, DEFAULT_POWER_SMOOTHING_S),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0,
                                max=300,
                                step=1,
                                unit_of_measurement="s",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
            )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle schedule options."""
        if user_input is not None:
            # Convert day strings back to integers
            if CONF_SCHEDULE_DAYS in user_input:
                user_input[CONF_SCHEDULE_DAYS] = [
                    int(d) for d in user_input[CONF_SCHEDULE_DAYS]
                ]
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current = self._config_entry.data
        current_days = current.get(CONF_SCHEDULE_DAYS, DEFAULT_SCHEDULE_DAYS)

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCHEDULE_ENABLED,
                        default=current.get(CONF_SCHEDULE_ENABLED, DEFAULT_SCHEDULE_ENABLED),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_SCHEDULE_START,
                        default=current.get(CONF_SCHEDULE_START, DEFAULT_SCHEDULE_START),
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_SCHEDULE_END,
                        default=current.get(CONF_SCHEDULE_END, DEFAULT_SCHEDULE_END),
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_SCHEDULE_DAYS,
                        default=[str(d) for d in current_days],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=d["value"], label=d["label"])
                                for d in WEEKDAYS
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_auto_off(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle auto-off timer options."""
        if user_input is not None:
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current = self._config_entry.data

        return self.async_show_form(
            step_id="auto_off",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTO_OFF_ENABLED,
                        default=current.get(CONF_AUTO_OFF_ENABLED, DEFAULT_AUTO_OFF_ENABLED),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_AUTO_OFF_MINUTES,
                        default=current.get(CONF_AUTO_OFF_MINUTES, DEFAULT_AUTO_OFF_MINUTES),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=1440,
                            step=1,
                            unit_of_measurement="min",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    async def async_step_reset(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reset counters."""
        if user_input is not None:
            # Get controller and reset counters
            ctrl = self.hass.data[DOMAIN].get(self._config_entry.entry_id)
            if ctrl:
                if user_input.get("reset_all"):
                    ctrl.reset_all_counters()
                    _LOGGER.info("All counters reset via options flow")
                elif user_input.get("reset_today"):
                    ctrl.reset_today_counters()
                    _LOGGER.info("Today's counters reset via options flow")
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="reset",
            data_schema=vol.Schema(
                {
                    vol.Optional("reset_all", default=False): selector.BooleanSelector(
                        selector.BooleanSelectorConfig()
                    ),
                    vol.Optional("reset_today", default=False): selector.BooleanSelector(
                        selector.BooleanSelectorConfig()
                    ),
                }
            ),
        )
