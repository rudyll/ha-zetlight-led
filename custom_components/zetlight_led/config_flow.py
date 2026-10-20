"""Config flow for the Zetlight Horizon Aqua LED integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from . import ZetlightClient, ZetlightUDPError
from .const import CONF_DEVICE_CODE, DEFAULT_PORT, DOMAIN
from . import protocol

_LOGGER = logging.getLogger(__name__)


class ZetlightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zetlight M5."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual host entry.

        Validation sends a read-status (0x0C) probe to the host. A reply both
        confirms the device is reachable over local UDP and gives us its real
        device code and name, which we store in the entry.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            client = ZetlightClient(
                self.hass, host, port, protocol.DEFAULT_DEVICE_CODE
            )
            try:
                await client.async_connect()
                status = await client.async_read_status()
            except ZetlightUDPError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surface anything else as generic
                _LOGGER.exception("Unexpected error probing %s", host)
                errors["base"] = "unknown"
            else:
                device_code = client.device_code.hex().upper()
                await self.async_set_unique_id(device_code)
                self._abort_if_unique_id_configured()
                client.close()
                return self.async_create_entry(
                    title=status.name or f"Zetlight LED ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_DEVICE_CODE: device_code,
                    },
                )
            client.close()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
