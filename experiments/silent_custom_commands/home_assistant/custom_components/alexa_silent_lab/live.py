"""Pure data builder for the first, unsuppressed, live Echo test."""
TEST_ENTITY = "media_player.living_room_echo"
TEST_COMMAND = "Set an alarm for 8 a.m. to play ABBA on Amazon Music"


def build_live_service_data(entity_id: str) -> dict:
    """Restrict the experiment to the specifically approved test Echo."""
    if entity_id != TEST_ENTITY:
        raise ValueError("Live test is restricted to " + TEST_ENTITY)
    return {
        "entity_id": TEST_ENTITY,
        "media_content_type": "custom",
        "media_content_id": TEST_COMMAND,
    }
