"""V5: inspect installed AlexaPy and opt-in direct sequence experiment."""
from __future__ import annotations
import ast
import inspect
import textwrap

ENTITY_ID = "media_player.living_room_echo"
COMMAND = "Set an alarm for 8 a.m. to play ABBA on Amazon Music"
FLAG = "suppressResponse"

def _skill_id():
    """Read the installed run_custom skillId literal; fail closed if changed."""
    from alexapy.alexaapi import AlexaAPI
    tree = ast.parse(textwrap.dedent(inspect.getsource(AlexaAPI.run_custom)))
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "send_sequence":
            for keyword in node.keywords:
                if keyword.arg == "skillId" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    matches.append(keyword.value.value)
    if len(matches) != 1:
        raise RuntimeError("Cannot safely identify installed AlexaPy run_custom skillId")
    return matches[0]

def preview():
    from alexapy.alexaapi import AlexaAPI
    # Verify code shape before permitting the live experiment.
    src = ast.parse(textwrap.dedent(inspect.getsource(AlexaAPI.send_sequence)))
    found = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "update" and isinstance(n.func.value, ast.Name) and n.func.value.id == "operation_payload" and any(isinstance(a, ast.Name) and a.id == "kwargs" for a in n.args) for n in ast.walk(src))
    if not found:
        raise RuntimeError("Installed send_sequence does not forward kwargs into operation_payload")
    _skill_id()
    return {"mode":"offline_verified_code_path", "amazon_request_sent":False, "entity_id":ENTITY_ID, "command":COMMAND, "candidate_operation_payload_delta":{FLAG:True}, "send_sequence_kwargs_forwarded":True, "suppression_supported_by_amazon":False, "warning":"Request structure only; Amazon support and silence unverified."}

def _find_player(hass):
    accounts = hass.data.get("alexa_media", {}).get("accounts", {})
    matches = []
    for account in accounts.values():
        for player in account.get("entities", {}).get("media_player", {}).values():
            if getattr(player, "entity_id", None) == ENTITY_ID:
                matches.append(player)
    if len(matches) != 1:
        raise RuntimeError("Cannot uniquely find living room Echo in Alexa Media Player account entities")
    return matches[0]

async def live(hass):
    preview()  # fail closed before any Amazon request
    player = _find_player(hass)
    api = getattr(player, "alexa_api", None)
    if api is None:
        raise RuntimeError("Target Alexa Media Player has no Alexa API")
    await api.send_sequence(
        "Alexa.TextCommand",
        customer_id=getattr(player, "_customer_id", None),
        queue_delay=0,
        skillId=_skill_id(),
        text=COMMAND,
        suppressResponse=True,
    )
    return {"mode":"live_v5_direct_operation_payload_candidate","requested":True,"entity_id":ENTITY_ID,"command":COMMAND,"flag_sent_into_alexapy_operation_payload":True,"suppression_verified":False,"note":"Amazon acceptance and actual alarm/silence must be checked on Echo and Alexa app."}
