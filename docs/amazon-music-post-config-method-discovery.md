# Browser HAR finding: POST config.json supplies CSRF metadata (2026-11-12)

Research only; not part of PR #3687. A user-supplied HAR was examined **locally**. Do not commit the HAR, tokens, cookies, account IDs, or raw authenticated request/response contents.

## Verified in HAR `music.amazon.co.uk(3).har`

Four requests to the same config URL:
`https://music.amazon.co.uk/config.json?skipToken=false&clientApplication=skyfire`.

| Request | Status | Response `csrf` object | Nested fields |
|---|---|---|---|
| POST (entry 0) | 200 | present | `rnd`, `token`, `ts` |
| GET (entry 24) | 200 | absent | none |
| POST (entry 25) | 200 | present | `rnd`, `token`, `ts` |
| GET (entry 41) | 200 | absent | none |

POST has no observed request body; browser request headers include Origin
and Referer. The GET/POST difference invalidates the earlier interpretation
that v8's missing CSRF proves AlexaPy authorization is inadequate: **v8 used
GET, and the browser GET also lacks CSRF.**

One successful search: `POST https://eu.web.skill.music.a2z.com/api/showSearch`
(status 200). Body properties: `filter`, `keyword`, `suggestedKeyword`,
`userHash`, `headers`. The first, second and fourth are JSON-serialized
values; `keyword` object has `interface` and `keyword`; `filter`
object has `IsLibrary`; `userHash` has `level`. `headers` includes
`x-amzn-authentication` and `x-amzn-csrf` properties. Successful response
top-level property: `methods`. Do not assume an existing AlexaPy session
will have these web-player auth values.

## Next diagnostic (strict read-only, no playback)

1. Test **POST** config URL with no body and no credential forwarding from
   AlexaPy; use both clean and existing AlexaPy sessions, comparing status,
   presence of `csrf.token`, and auth-field-presence booleans only.
2. If config POST succeeds, investigate constructing a read-only `showSearch`
   request with the *same field types* as the HAR. Do not transplant captured
   browser tokens into Home Assistant, logs, or GitHub.
3. HTTP 200/search results are not native `musicAlarmId` UUIDs. The
   catalogue-to-alarm selection bridge remains unsolved.

No endpoints that trigger Alexa speech, music playback, or alarm writes were
sent during this HAR investigation.
