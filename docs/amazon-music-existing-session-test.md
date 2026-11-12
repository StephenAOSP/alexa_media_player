# Existing AlexaPy session versus Amazon Music GraphQL — research test v4

## Verified observations (12 November 2026)

* Amazon Music UK's HTML search route responds with status 200 but contains no server-rendered music results in the Home Assistant probe.
* A browser capture of the same music-search UI showed the POST endpoint `https://gql.music.amazon.co.uk/` and the `SpecSearchPage` operation. The browser retrieved artist, album and track catalogue records.
* A standalone anonymous read-only POST to `SpecSearchPage` from Home Assistant returned **401 Unauthorized**. The existence of an authenticated browser response does not prove that AlexaPy's authentication authorizes this service.
* AlexaPy exposes an existing `AlexaLogin.session` (an `aiohttp.ClientSession`); Alexa Media Player also uses `login._session` for authenticated requests to Alexa endpoints. Cookie domain scoping and service-specific permissions matter.

## Next experiment: existing-session compatibility

A separate v4 Home Assistant test ZIP was built, without replacing the current native-alarm PR.

* The test action remains `alexa_media.search_music_catalog`, with `entity_id` and `query: Enya`.
* It sends one POST to the account's allowlisted regional `gql.music.<marketplace>` endpoint using **only the existing AlexaPy session**. It supplies no copied browser cookies, browser API keys, CSRF tokens, or explicitly copied authorization headers.
* It does not start playback, create alarms, or store music identifiers.
* Diagnostics return HTTP status, content type, outcome, recognized GraphQL error codes, catalogue matches, and only the NUMBER of cookies applicable to the target hostname. Cookie names, values, secrets, headers, account identifiers and unfiltered responses are never returned.
* A 401/403 indicates the existing Alexa session does not authorize this particular GraphQL operation as called; zero applicable cookies would provide further evidence of domain scope mismatch.
* Even a successful catalogue ID does **not** resolve an Alexa native `musicAlarmId` UUID. That problem remains separate.

## Limitations

* The v4 ZIP is a locally packaged research build based on the earlier v3.1 diagnostic, not a production-ready integration and not an exact branch checkout. It has syntax, YAML, and ZIP-integrity checks; the live authenticated-session request needs Home Assistant testing.
* An AlexaPy session may share Amazon SSO cookies in some environments but have different permissions, host scoping, or authentication mechanism from the Music website; **no result is assumed in advance**.
* Preserve PR #3687 as a separate change. Never place experimental lookup behavior or persistent music IDs into that PR without a successful and reviewed proof.
