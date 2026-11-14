"""Alexa Silent Lab: isolated offline preview and opt-in live baseline test."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import voluptuous as vol

from .preview import build_preview
from .live import build_live_service_data, TEST_ENTITY

DOMAIN = "alexa_silent_lab"
PREVIEW_SCHEMA = vol.Schema({
    vol.Required("command"): vol.All(str, vol.Length(min=1)),
    vol.Optional("suppress_response", default=True): bool,
})
LIVE_SCHEMA = vol.Schema({
    vol.Required("confirm_live_test"): vol.In([True]),
    vol.Optional("entity_id", default=TEST_ENTITY): vol.In([TEST_ENTITY]),
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register separate lab actions; never modify the Alexa integration."""
    async def preview_custom(call: ServiceCall) -> dict:
        return build_preview(call.data["command"], call.data["suppress_response"])

    async def live_baseline(call: ServiceCall) -> dict:
        """Send a normal custom command through existing Alexa Media Player."""
        data = build_live_service_data(call.data["entity_id"])
        await hass.services.async_call("media_player", "play_media", data, blocking=True)
        return {
            "requested": True,
            "entity_id": data["entity_id"],
            "command": data["media_content_id"],
            "mode": "live_baseline_no_suppression",
            "note": "Service call returned; Alexa execution and alarm creation are not verified.",
        }

    hass.services.async_register(
        DOMAIN, "preview_custom", preview_custom,
        schema=PREVIEW_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "live_baseline", live_baseline,
        schema=LIVE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    return True
