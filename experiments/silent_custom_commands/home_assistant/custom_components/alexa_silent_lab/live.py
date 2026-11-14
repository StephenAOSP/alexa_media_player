"""Opt-in Alexa Media Player service payloads. No independent Alexa login."""
TEST_ENTITY = "media_player.living_room_echo"
TEST_COMMAND = "Set an alarm for 8 a.m. to play ABBA on Amazon Music"

def build_live_service_data(entity_id: str, candidate: bool = False) -> dict:
    if entity_id != TEST_ENTITY:
        raise ValueError("Live test is restricted to " + TEST_ENTITY)
    data = {
        "entity_id": TEST_ENTITY,
        "media_content_type": "custom",
        "media_content_id": TEST_COMMAND,
    }
    if candidate:
        # Unverified hypothesis. HA forwards 'extra' to async_play_media as
        # kwargs, which forwards it to AlexaPy's run_custom. Whether Amazon
        # accepts this field is not established.
        data["extra"] = {"suppressResponse": True}
    return data
