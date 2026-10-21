"""Config and options flow for the Zetlight Horizon Aqua LED integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
)

from . import ZetlightClient, ZetlightUDPError, async_discover, preset_to_args, protocol
from .const import CONF_DEVICE_CODE, CONF_PRESETS, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

_MANUAL = "__manual__"


class ZetlightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zetlight Horizon Aqua LED."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer discovered devices, or fall through to manual entry."""
        if user_input is not None:
            choice = user_input["device"]
            if choice == _MANUAL:
                return await self.async_step_manual()
            return await self._async_create(choice)

        self._discovered = await async_discover(self.hass)
        if not self._discovered:
            return await self.async_step_manual()

        choices = {d["host"]: f"{d['name']} ({d['host']})" for d in self._discovered}
        choices[_MANUAL] = "Enter IP manually"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("device"): vol.In(choices)}),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual host entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_create(
                user_input[CONF_HOST], user_input.get(CONF_PORT, DEFAULT_PORT), errors
            )
            if result is not None:
                return result

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="manual", data_schema=schema, errors=errors
        )

    async def _async_create(
        self, host: str, port: int = DEFAULT_PORT, errors: dict | None = None
    ) -> ConfigFlowResult | None:
        """Probe the host and create the entry; returns None on failure (manual)."""
        client = ZetlightClient(self.hass, host, port, protocol.DEFAULT_DEVICE_CODE)
        try:
            await client.async_connect()
            status = await client.async_read_status()
        except ZetlightUDPError:
            if errors is not None:
                errors["base"] = "cannot_connect"
            client.close()
            return None if errors is not None else self.async_abort(reason="cannot_connect")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error probing %s", host)
            if errors is not None:
                errors["base"] = "unknown"
            client.close()
            return None if errors is not None else self.async_abort(reason="unknown")

        device_code = client.device_code.hex().upper()
        client.close()
        await self.async_set_unique_id(device_code)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=status.name or f"Zetlight LED ({host})",
            data={
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_DEVICE_CODE: device_code,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return ZetlightOptionsFlow()


_PRESET_EXAMPLE = {
    "LPS day": {
        "start": "09:00",
        "durations": [60, 120, 480, 120, 120],
        "brightness": [
            [10, 40, 30, 10],
            [20, 60, 45, 20],
            [40, 90, 70, 40],
            [20, 60, 45, 20],
            [5, 25, 18, 5],
        ],
    }
}


class ZetlightOptionsFlow(OptionsFlow):
    """Manage named schedule presets (as YAML)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            text = user_input.get(CONF_PRESETS, "").strip()
            try:
                presets = yaml.safe_load(text) if text else {}
                if presets and not isinstance(presets, dict):
                    raise ValueError("top level must be a mapping of name -> preset")
                for name, preset in (presets or {}).items():
                    preset_to_args(preset)  # validate each
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Preset parse error: %s", err)
                errors["base"] = "invalid_presets"
            else:
                return self.async_create_entry(
                    title="", data={CONF_PRESETS: presets or {}}
                )

        current = self.config_entry.options.get(CONF_PRESETS)
        default = yaml.safe_dump(
            current if current else _PRESET_EXAMPLE, sort_keys=False, allow_unicode=True
        )
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PRESETS, default=default
                ): TextSelector(TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
