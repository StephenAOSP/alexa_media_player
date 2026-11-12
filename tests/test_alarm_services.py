"""Tests for the create, enable, disable and delete alarm services."""

import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexaAPI, AlexapyLoginError
from alexapy.errors import AlexapyConnectionError, AlexapyTooManyRequestsError
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
import voluptuous as vol

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.services import (
    CREATE_ALARM_SCHEMA,
    AlexaMediaServices,
    next_alarm_time,
)

EMAIL = "test@example.com"
SERIAL = "G090XXXXXXXXXXXX"
DEVICE_TYPE = "A4ZXE0RM7LQ7A"
ENTITY_ID = "media_player.kitchen_echo"
# A Tuesday.
NOW = datetime.datetime(2026, 10, 20, 7, 0)
ALARM = {
    "id": f"{DEVICE_TYPE}-{SERIAL}-idx-1",
    "notificationIndex": "idx-1",
    "type": "Alarm",
    "originalTime": "06:30:00.000",
    "originalDate": "2026-10-01",
    "recurringPattern": None,
    "status": "OFF",
    "sound": {"id": "system_alerts_melodic_02"},
    "date_time": datetime.datetime(2026, 10, 1, 6, 30),
}


@pytest.fixture(autouse=True)
def frozen_now():
    with patch("custom_components.alexa_media.services.dt_util.now", return_value=NOW):
        yield


def make_services(alarm=ALARM):
    login = MagicMock(email=EMAIL, url="amazon.co.uk")
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {"notifications": {SERIAL: {"Alarm": {"idx-1": alarm}}}}
            }
        }
    }
    schedule = MagicMock()
    services = AlexaMediaServices(
        hass, functions={"schedule_notifications_refresh": schedule}
    )
    services._resolve_device = MagicMock(return_value=(login, SERIAL, DEVICE_TYPE))
    return services, login, schedule


def call(**data):
    return MagicMock(data={"entity_id": ENTITY_ID, **data})


RECURRING_ALARM = {
    **ALARM,
    "deviceSerialNumber": SERIAL,
    "deviceType": DEVICE_TYPE,
    "alarmLabel": "Weekday test alarm",
    "originalDate": "2026-10-21",
    "date_time": datetime.datetime(2026, 10, 21, 6, 30),
    "recurringPattern": "XXXX-WD",
    "status": "ON",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("alarm_id", [RECURRING_ALARM["id"], "idx-1"])
async def test_skip_next_alarm_registered(alarm_id):
    """Verify both alarm ID formats through the registered service."""
    services, login, schedule = make_services(RECURRING_ALARM.copy())
    del services._resolve_device
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["login_obj"] = login
    await services.register()
    registered = {
        args[1]: (args[2], kwargs["schema"])
        for args, kwargs in services.hass.services.async_register.call_args_list
    }
    handler, schema = registered["skip_next_alarm"]
    with (
        patch("custom_components.alexa_media.services.er.async_get") as registry,
        patch.object(
            AlexaAPI,
            "devices",
            {EMAIL: [{"serialNumber": SERIAL, "deviceType": DEVICE_TYPE}]},
        ),
        patch.object(
            AlexaAPI, "skip_next_alarm", autospec=True, return_value=True
        ) as skip,
    ):
        registry.return_value.async_get.return_value = MagicMock(
            platform="alexa_media", unique_id=SERIAL
        )
        assert await handler(MagicMock(data=schema(call(alarm_id=alarm_id).data)))

    registry.return_value.async_get.assert_called_once_with(ENTITY_ID)
    skip.assert_awaited_once_with(login, "idx-1")
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="skip_next_alarm"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "alarm_id"),
    [
        ({"recurringPattern": None}, "idx-1"),
        ({"status": "OFF"}, "idx-1"),
        ({"notificationIndex": None}, "idx-1"),
        ({}, f"{DEVICE_TYPE}-OTHER-SERIAL-idx-1"),
    ],
)
async def test_skip_next_alarm_rejects_invalid_target(changes, alarm_id):
    """Reject invalid alarm targets before calling Alexa or refreshing notifications."""
    services, _, schedule = make_services({**RECURRING_ALARM, **changes})
    with (
        patch.object(AlexaAPI, "skip_next_alarm", autospec=True) as skip,
        pytest.raises(ServiceValidationError),
    ):
        await services.skip_next_alarm(call(alarm_id=alarm_id))
    skip.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_skip_next_alarm_refused():
    """Report a refused skip without scheduling a notification refresh."""
    services, _, schedule = make_services(RECURRING_ALARM.copy())
    with (
        patch.object(AlexaAPI, "skip_next_alarm", autospec=True, return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await services.skip_next_alarm(call(alarm_id="idx-1"))
    schedule.assert_not_called()


@pytest.mark.parametrize(
    ("alarm_time", "days", "start", "expected"),
    [
        (datetime.time(7, 30), [], None, "2026-10-20T07:30:00"),
        (datetime.time(6, 30), [], None, "2026-10-21T06:30:00"),
        (datetime.time(7, 0), [], None, "2026-10-21T07:00:00"),
        (datetime.time(6, 30), ["tue"], None, "2026-10-27T06:30:00"),
        (datetime.time(6, 30), ["sat", "sun"], None, "2026-10-24T06:30:00"),
        (datetime.time(6, 30), [], datetime.date(2026, 10, 1), "2026-10-21T06:30:00"),
        (datetime.time(6, 30), [], datetime.date(2026, 10, 30), "2026-10-30T06:30:00"),
    ],
)
def test_next_alarm_time(alarm_time, days, start, expected):
    assert next_alarm_time(alarm_time, days, start) == expected


def test_create_schema():
    data = CREATE_ALARM_SCHEMA({"entity_id": ENTITY_ID, "time": "06:30"})
    assert data["time"] == datetime.time(6, 30)
    assert data["days"] == []
    with pytest.raises(vol.Invalid):
        CREATE_ALARM_SCHEMA(
            {"entity_id": ENTITY_ID, "time": "06:30", "days": ["monday"]}
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("days", "when", "recurrence"),
    [
        ([], "2026-10-21T06:30:00", None),
        (
            ["fri", "mon"],
            "2026-10-23T06:30:00",
            {"freq": "WEEKLY", "byDay": ["MO", "FR"], "interval": 1},
        ),
        (
            ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "2026-10-21T06:30:00",
            {"freq": "DAILY", "byDay": [], "interval": 1},
        ),
    ],
)
async def test_create_alarm(days, when, recurrence):
    services, login, schedule = make_services()
    with patch.object(
        AlexaAPI, "create_alarm", autospec=True, return_value=True
    ) as create:
        assert await services.create_alarm(call(time=datetime.time(6, 30), days=days))

    create.assert_awaited_once_with(login, SERIAL, DEVICE_TYPE, when, recurrence, None)
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="create_alarm"
    )


@pytest.mark.asyncio
async def test_create_alarm_failed():
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True, return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "when", "sound_id"),
    [
        ({}, "2026-10-21T06:30:00", "system_alerts_melodic_02"),
        (
            {"originalDate": "2026-10-30"},
            "2026-10-30T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {"recurringPattern": "XXXX-WD"},
            "2026-10-21T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {"recurringPattern": "XXXX-WE"},
            "2026-10-24T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {
                "recurringPattern": "XXXX-WXX-1",
                "rRuleData": {"byWeekDays": ["MO", "WE"]},
            },
            "2026-10-21T06:30:00",
            "system_alerts_melodic_02",
        ),
        ({"musicAlarmId": "music-1"}, "2026-10-21T06:30:00", "MUSIC-music-1"),
    ],
)
async def test_enable_alarm(changes, when, sound_id):
    services, login, schedule = make_services({**ALARM, **changes})
    with patch.object(
        AlexaAPI, "enable_alarm", autospec=True, return_value=True
    ) as enable:
        assert await services.enable_alarm(call(alarm_id="idx-1"))

    enable.assert_awaited_once_with(login, "idx-1", when, sound_id)
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="enable_alarm"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["originalTime", "originalDate"])
async def test_enable_alarm_without_time(missing):
    alarm = {k: v for k, v in ALARM.items() if k != missing}
    services, _, schedule = make_services(alarm)
    with (
        patch.object(AlexaAPI, "enable_alarm", autospec=True) as enable,
        pytest.raises(ServiceValidationError),
    ):
        await services.enable_alarm(call(alarm_id="idx-1"))
    enable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_enable_alarm_unknown_repeat():
    services, _, schedule = make_services({**ALARM, "recurringPattern": "P1M"})
    with (
        patch.object(AlexaAPI, "enable_alarm", autospec=True) as enable,
        pytest.raises(ServiceValidationError),
    ):
        await services.enable_alarm(call(alarm_id="idx-1"))
    enable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_disable_alarm_by_id():
    services, login, schedule = make_services()
    with patch.object(
        AlexaAPI, "disable_alarm", autospec=True, return_value=True
    ) as disable:
        assert await services.disable_alarm(call(alarm_id=ALARM["id"]))

    disable.assert_awaited_once_with(login, "idx-1")
    schedule.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "date_time", [datetime.datetime(2026, 10, 1, 6, 30), "2026-10-01 06:30:00.000"]
)
async def test_delete_alarm_drops_date_time(date_time):
    services, login, schedule = make_services({**ALARM, "date_time": date_time})
    with patch.object(
        AlexaAPI, "delete_notification", autospec=True, return_value=True
    ) as delete:
        assert await services.delete_alarm(call(alarm_id="idx-1"))

    sent = delete.call_args.args[1]
    assert delete.call_args.args[0] is login
    assert "date_time" not in sent
    assert sent["id"] == ALARM["id"]
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="delete_alarm"
    )


@pytest.mark.asyncio
async def test_delete_snoozed_alarm():
    """A snoozed alarm's snoozedToTime is a datetime once the sensor has seen it."""
    snoozed = {
        **ALARM,
        "status": "SNOOZED",
        "snoozedToTime": datetime.datetime(2026, 10, 20, 7, 9),
    }
    services, _, _ = make_services(snoozed)
    with patch.object(
        AlexaAPI, "delete_notification", autospec=True, return_value=True
    ) as delete:
        assert await services.delete_alarm(call(alarm_id="idx-1"))

    sent = delete.call_args.args[1]
    assert "snoozedToTime" not in sent
    json.dumps(sent)


@pytest.mark.asyncio
async def test_create_alarm_uses_echo_time_zone():
    """The next ring is worked out in the Echo's time zone, not HA's."""
    services, login, _ = make_services()
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["devices"] = {
        "media_player": {SERIAL: {"timeZoneId": "Asia/Tokyo"}}
    }
    tokyo = dt_util.get_time_zone("Asia/Tokyo")
    # 07:00 for HA, but already 16:00 on the Echo
    with (
        patch(
            "custom_components.alexa_media.services.dt_util.now",
            side_effect=lambda tz=None: (
                NOW + datetime.timedelta(hours=9) if tz is tokyo else NOW
            ),
        ),
        patch.object(
            AlexaAPI, "create_alarm", autospec=True, return_value=True
        ) as create,
    ):
        await services.create_alarm(call(time=datetime.time(8, 0), days=[]))

    assert create.call_args.args[3] == "2026-10-21T08:00:00"


@pytest.mark.asyncio
async def test_delete_alarm_failed():
    services, _, schedule = make_services()
    with (
        patch.object(
            AlexaAPI, "delete_notification", autospec=True, return_value=False
        ),
        pytest.raises(HomeAssistantError),
    ):
        await services.delete_alarm(call(alarm_id="idx-1"))
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("logged_in", [True, False])
async def test_alarm_login_error(logged_in):
    services, login, schedule = make_services()
    login.test_loggedin = AsyncMock(return_value=logged_in)
    with (
        patch.object(
            AlexaAPI, "disable_alarm", autospec=True, side_effect=AlexapyLoginError
        ),
        patch(
            "custom_components.alexa_media.services.report_relogin_required"
        ) as relogin,
        pytest.raises(HomeAssistantError),
    ):
        await services.disable_alarm(call(alarm_id="idx-1"))
    assert relogin.called is not logged_in
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [AlexapyConnectionError, AlexapyTooManyRequestsError, TimeoutError]
)
async def test_alarm_amazon_unreachable(error):
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True, side_effect=error),
        pytest.raises(HomeAssistantError),
    ):
        await services.create_alarm(call(time=datetime.time(7, 0), days=[]))
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_alarm():
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "disable_alarm", autospec=True) as disable,
        pytest.raises(ServiceValidationError),
    ):
        await services.disable_alarm(call(alarm_id="missing"))
    disable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_device():
    services, _, _ = make_services()
    services._resolve_device.return_value = (None, None, None)
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError),
    ):
        await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
    create.assert_not_awaited()


@pytest.mark.parametrize("preset", ["today", "tomorrow"])
def test_date_presets_require_echo_timezone(preset):
    """Do not substitute HA's timezone when Echo timezone is unknown."""
    from custom_components.alexa_media.services import resolve_alarm_schedule

    with pytest.raises(ServiceValidationError, match="Echo's timezone is unavailable"):
        resolve_alarm_schedule(datetime.time(8, 0), [preset], None)


def test_music_asset_store_is_private():
    """Learned music selection names should not be world-readable."""
    services, login, _ = make_services()
    with patch("custom_components.alexa_media.services.Store") as store:
        services._music_store(login)

    assert store.call_args.kwargs["private"] is True


MUSIC_ALARM_ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
async def test_music_resolver_uses_learned_asset_before_lookup():
    """Existing alarm selections must not trigger a provider lookup."""
    services, login, _ = make_services()
    provider_lookup = AsyncMock(return_value=None)
    services._functions["resolve_music_alarm_asset"] = provider_lookup
    with patch.object(
        services,
        "_learn_music_assets",
        new_callable=AsyncMock,
        return_value={services._music_key("Amazon Music", "Enya"): MUSIC_ALARM_ID},
    ):
        assert (
            await services.resolve_music_alarm_asset(login, "Amazon Music", "Enya")
            == MUSIC_ALARM_ID
        )
    provider_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_music_resolver_accepts_verified_new_asset():
    """A future read-only provider adapter can return a native alarm identifier."""
    services, login, _ = make_services()
    lookup = AsyncMock(return_value=MUSIC_ALARM_ID)
    services._functions["resolve_music_alarm_asset"] = lookup
    with patch.object(
        services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
    ):
        result = await services.resolve_music_alarm_asset(
            login, "Amazon Music", "Enya"
        )
    assert result == MUSIC_ALARM_ID
    lookup.assert_awaited_once_with(login, "Amazon Music", "Enya", "amazon.co.uk")


@pytest.mark.asyncio
async def test_music_resolver_rejects_unknown_selection_without_playback():
    """Never create an alarm or start playback if no music identifier exists."""
    services, login, _ = make_services()
    with (
        patch.object(
            services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
        ),
        patch.object(AlexaAPI, "play_music", autospec=True) as playback,
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="read-only lookup"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 15),
                days=[],
                alarm_type="music",
                music_entity="Enya",
                music_provider="Amazon Music",
            )
        )
    playback.assert_not_called()
    create.assert_not_called()


@pytest.mark.asyncio
async def test_music_resolver_rejects_catalogue_or_invalid_asset_id():
    """A provider lookup cannot pass arbitrary playback IDs into Alexa alarms."""
    services, login, _ = make_services()
    services._functions["resolve_music_alarm_asset"] = AsyncMock(
        return_value="catalogue:enya:artist"
    )
    with (
        patch.object(
            services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
        ),
        pytest.raises(ServiceValidationError, match="identifier is invalid"),
    ):
        await services.resolve_music_alarm_asset(login, "Amazon Music", "Enya")


@pytest.mark.asyncio
async def test_music_resolver_creates_alarm_with_verified_new_asset():
    """Only a verified native asset ID reaches the alarm creation API."""
    services, login, schedule = make_services()
    services._functions["resolve_music_alarm_asset"] = AsyncMock(
        return_value=MUSIC_ALARM_ID
    )
    with (
        patch.object(
            services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
        ),
        patch.object(
            AlexaAPI, "create_alarm", autospec=True, return_value=True
        ) as create,
    ):
        assert await services.create_alarm(
            call(
                time=datetime.time(8, 15),
                days=[],
                alarm_type="music",
                music_entity="Enya",
                music_provider="Amazon Music",
            )
        )
    create.assert_awaited_once_with(
        login,
        SERIAL,
        DEVICE_TYPE,
        "2026-10-20T08:15:00",
        None,
        f"MUSIC-{MUSIC_ALARM_ID}",
    )
    schedule.assert_called_once()


@pytest.mark.asyncio
async def test_music_alarm_metadata_inspection_is_read_only():
    """Only safe metadata and hashed identifiers are returned."""
    music_id = "11111111-1111-4111-8111-111111111111"
    alarm = {
        "provider": "Amazon Music",
        "musicEntity": "Enya",
        "musicAlarmId": music_id,
        "status": "ON",
        "recurringPattern": None,
        "notificationIndex": "private-alarm-id",
    }
    services, login, _ = make_services(alarm)
    services._resolve_alarm_device = MagicMock(
        return_value=(login, SERIAL, DEVICE_TYPE, None)
    )
    with (
        patch.object(
            AlexaAPI, "create_alarm", autospec=True
        ) as create,
        patch.object(
            AlexaAPI, "play_music", autospec=True
        ) as play,
        patch.object(services, "_music_store") as store,
    ):
        result = await services.inspect_music_alarm_metadata(call())

    assert result["cached_music_alarm_count"] == 1
    entry = result["alarms"][0]
    assert entry["music_entity"] == "Enya"
    assert entry["provider"] == "Amazon Music"
    assert entry["music_id_present"] is True
    assert entry["music_id_uuid_format"] is True
    assert len(entry["music_id_fingerprint"]) == 16
    assert music_id not in str(result)
    assert "private-alarm-id" not in str(result)
    store.assert_not_called()
    create.assert_not_called()
    play.assert_not_called()


@pytest.mark.asyncio
async def test_music_alarm_metadata_inspection_empty_cache():
    services, login, _ = make_services({})
    services._resolve_alarm_device = MagicMock(
        return_value=(login, SERIAL, DEVICE_TYPE, None)
    )
    result = await services.inspect_music_alarm_metadata(call())
    assert result["cached_music_alarm_count"] == 0
    assert result["alarms"] == []


@pytest.mark.parametrize(
    ("account_domain", "marketplace"),
    [
        ("amazon.co.uk", "amazon.co.uk"),
        ("https://www.amazon.com", "amazon.com"),
        ("amazon.de", "amazon.de"),
        ("www.amazon.co.jp", "amazon.co.jp"),
        ("amazon.com.au", "amazon.com.au"),
        ("https://subdomain.amazon.co.uk", None),
        ("https://example.com", None),
        ("", None),
        (None, None),
    ],
)
def test_music_resolver_marketplace_from_alexa_account(
    account_domain, marketplace
):
    """Use the Alexa account domain; never infer from HA timezone or location."""
    services, login, _ = make_services()
    login.url = account_domain
    assert services._amazon_account_marketplace(login) == marketplace


@pytest.mark.asyncio
async def test_music_resolver_does_not_query_unknown_marketplace():
    """Unknown account region should not be searched or create an alarm."""
    services, login, _ = make_services()
    login.url = "example.com"
    lookup = AsyncMock(return_value=MUSIC_ALARM_ID)
    services._functions["resolve_music_alarm_asset"] = lookup
    with (
        patch.object(
            services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
        ),
        pytest.raises(ServiceValidationError, match="marketplace"),
    ):
        await services.resolve_music_alarm_asset(login, "Amazon Music", "Enya")
    lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_music_resolver_never_queries_new_radio_selections():
    """Existing learned radio support stays intact; Amazon-only search is isolated."""
    services, login, _ = make_services()
    lookup = AsyncMock(return_value=MUSIC_ALARM_ID)
    services._functions["resolve_music_alarm_asset"] = lookup
    with (
        patch.object(
            services, "_learn_music_assets", new_callable=AsyncMock, return_value={}
        ),
        pytest.raises(ServiceValidationError, match="No music-alarm identifier"),
    ):
        await services.resolve_music_alarm_asset(login, "Global Player", "Radio X UK")
    lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_music_catalog_returns_account_marketplace_candidates():
    """GraphQL diagnostic only; never create an alarm or start playback."""
    services, login, _ = make_services()
    login.url = "amazon.co.uk"
    services._resolve_alarm_device = MagicMock(
        return_value=(login, SERIAL, DEVICE_TYPE, None)
    )
    candidate = {
        "name": "Enya",
        "type": "artist",
        "catalog_id": "B001ED54MQ",
        "exact_name_match": True,
    }
    with (
        patch(
            "custom_components.alexa_media.services.probe_anonymous_graphql",
            new_callable=AsyncMock,
            return_value={
                "outcome": "catalogue_results",
                "http_status": 200,
                "content_type": "application/json",
                "candidates": [candidate],
            },
        ) as probe,
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        patch.object(AlexaAPI, "play_music", autospec=True) as play,
    ):
        result = await services.search_music_catalog(call(query="Enya"))

    assert result["marketplace"] == "amazon.co.uk"
    assert result["candidates"][0]["catalog_id"] == "B001ED54MQ"
    assert result["diagnostics"]["outcome"] == "catalogue_results"
    probe.assert_awaited_once_with(marketplace="amazon.co.uk", query="Enya")
    create.assert_not_called()
    play.assert_not_called()


@pytest.mark.asyncio
async def test_search_music_catalog_rejects_unknown_account_marketplace():
    services, login, _ = make_services()
    login.url = "example.org"
    services._resolve_alarm_device = MagicMock(
        return_value=(login, SERIAL, DEVICE_TYPE, None)
    )
    with pytest.raises(ServiceValidationError, match="marketplace"):
        await services.search_music_catalog(call(query="Enya"))
