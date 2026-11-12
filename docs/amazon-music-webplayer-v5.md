# UK Amazon Music web-player lookup research (v5)

Source inspiration: [notdeltaxd/Amazon-Music-API](https://github.com/notdeltaxd/Amazon-Music-API) (MIT, unofficial metadata-only implementation).

The project uses the UK `https://music.amazon.co.uk/config.json` configuration and the EU web-player metadata endpoint `POST https://eu.mesk.skill.music.a2z.com/api/searchCatalogArtists`. This is a distinct API from the `SpecSearchPage` GraphQL endpoint. It sends `keyword: Enya` with a web-player context derived from the site configuration.

**Test v5** is a temporary Home Assistant ZIP diagnostic, not production code or part of PR #3687. It fetches config in memory and attempts one artist metadata search only if the required configuration fields exist. It returns HTTP statuses, presence-only flags, and validated artist names/catalogue IDs. No tokens, cookies, CSRF values, raw responses or HAR files are committed. It never plays music or creates alarms. Live response is *not verified*.

Prior experiments: public HTML search had zero parseable links; unauthenticated GraphQL HTTP 401; GraphQL using AlexaPy session HTTP 401 despite 12 domain-applicable cookies. These do not establish whether the web-player endpoint works.

Even a working artist name -> ASIN lookup **does not resolve the ASIN -> UUID-format Alexa native musicAlarmId**. The native-alarm PR stays separate and unchanged.
