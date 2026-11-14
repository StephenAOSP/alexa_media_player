"""Alexa Silent Lab: opt-in live comparison, isolated from Alexa Media Player."""
from __future__ import annotations
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import voluptuous as vol
from .preview import build_preview
from .v61_targeted import inspect_v61
from .v6_inventory import inventory as v6_inventory
from .v5_experiment import preview as v5_preview, live as v5_live
from .request_diagnostic import inspect_request_builders
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
    async def preview_custom(call: ServiceCall) -> dict:
        return build_preview(call.data["command"], call.data["suppress_response"])

    async def run_live(call: ServiceCall, candidate: bool) -> dict:
        data = build_live_service_data(call.data["entity_id"], candidate=candidate)
        await hass.services.async_call("media_player", "play_media", data, blocking=True)
        return {
            "requested": True,
            "entity_id": data["entity_id"],
            "command": data["media_content_id"],
            "mode": "live_candidate_unverified" if candidate else "live_baseline_no_suppression",
            "suppression_requested": candidate,
            "suppression_verified": False,
            "note": "Call returned; Alexa execution, alarm creation and suppression are not verified. Observe the Echo and check Alexa app.",
        }

    async def live_baseline(call: ServiceCall) -> dict:
        return await run_live(call, candidate=False)

    async def live_candidate(call: ServiceCall) -> dict:
        return await run_live(call, candidate=True)

    async def inspect_request_path(call: ServiceCall) -> dict:
        return await hass.async_add_executor_job(inspect_request_builders)

    hass.services.async_register(DOMAIN, "inspect_request_path", inspect_request_path,
        supports_response=SupportsResponse.ONLY)
    async def preview_v5(call: ServiceCall) -> dict:
        return await hass.async_add_executor_job(v5_preview)

    async def live_v5(call: ServiceCall) -> dict:
        return await v5_live(hass)

    hass.services.async_register(DOMAIN, "preview_v5", preview_v5,
        supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "live_v5", live_v5,
        schema=vol.Schema({vol.Required("confirm_live_test"): vol.In([True])}),
        supports_response=SupportsResponse.ONLY)
    async def inspect_v6(call: ServiceCall) -> dict:
        return await hass.async_add_executor_job(v6_inventory)

    hass.services.async_register(DOMAIN, "inspect_v6", inspect_v6,
        supports_response=SupportsResponse.ONLY)
    async def inspect_v61_service(call: ServiceCall) -> dict:
        return await hass.async_add_executor_job(inspect_v61)

    hass.services.async_register(DOMAIN, "inspect_v61", inspect_v61_service,
        supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "preview_custom", preview_custom,
        schema=PREVIEW_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "live_baseline", live_baseline,
        schema=LIVE_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "live_candidate", live_candidate,
        schema=LIVE_SCHEMA, supports_response=SupportsResponse.ONLY)
    return True
