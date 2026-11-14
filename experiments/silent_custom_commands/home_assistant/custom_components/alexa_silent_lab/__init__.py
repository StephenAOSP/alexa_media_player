"""Alexa Silent Lab: independent, offline-only Home Assistant test integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import voluptuous as vol

from .preview import build_preview

DOMAIN = "alexa_silent_lab"
SERVICE_PREVIEW = "preview_custom"
SCHEMA = vol.Schema(
    {
        vol.Required("command"): vol.All(str, vol.Length(min=1)),
        vol.Optional("suppress_response", default=True): bool,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register a preview service. Never log in to Alexa or send commands."""

    async def preview_custom(call: ServiceCall) -> dict:
        return build_preview(
            call.data["command"], call.data["suppress_response"]
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIEW,
        preview_custom,
        schema=SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True
