# API reference

Open `/docs` for the generated request and response schemas. Invalid fields return 422; unauthenticated requests 401; another owner's resource 404; unavailable watering/action conflicts 409; request limits 429; database failure 503. All payloads are JSON.

## Accounts

| Method | Endpoint | Request / result |
|---|---|---|
| POST | /api/auth/register | name, email, password (10–128 chars) → session, one-time recovery_code, private three-plant garden |
| POST | /api/auth/login | email, password → session and access_token |
| POST | /api/auth/demo | No body → private one-hour guest garden |
| GET | /api/auth/me | Authenticated name and demo status |
| POST | /api/auth/logout | Clears browser cookie |
| POST | /api/auth/recover | email, new password in `password`, recovery_code → rotated code/session; old tokens revoked |
| DELETE | /api/auth/account | Authenticated password confirmation → account/data deletion |

The browser uses an HttpOnly cookie. Programmatic user API calls may use `Authorization: Bearer TOKEN`. Tokens last one hour. Do not embed a token or password in a shared URL. Emails are normalized and syntax-checked, not externally verified.

## Plants, controls and history

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | Database readiness and version |
| GET | /api/devices | Owned devices, readings, virtual/external mode and live state |
| POST | /api/devices | plant_name, plant_type, location, mode (`virtual` default or `external`) → new plant; max 12 |
| GET | /api/devices/{id} | Selected device |
| GET | /api/devices/{id}/latest | Latest sample |
| GET | /api/devices/{id}/history | limit 1–1000, optional Unix `before`; chronological page |
| PUT | /api/devices/{id}/threshold | moisture_threshold 5–80 and auto_water boolean |
| POST | /api/devices/{id}/water | duration 1–15 seconds, default 10; guard checks apply |
| POST | /api/devices/{id}/stop | Cancel current command |
| POST | /api/devices/{id}/simulation | action `start`, `pause`, `dry` or `refill`; virtual plants only |
| GET | /api/devices/{id}/watering-history | Latest 100 commands |
| GET | /api/alerts | Latest 100 owned alerts |
| PUT | /api/alerts/{id}/acknowledge | Mark an open alert acknowledged |

All routes above except health require user identity. A key returned for an externally connected plant is shown only at creation; save it privately. Virtual plants require no device key from visitors.

## External sensor API

`POST /api/sensors/data` and `GET /api/devices/{id}/command` require `X-Device-Key`. Only an external-mode plant accepts ingestion. The JSON fields are device_id, unique sample_id, soil_moisture, temperature, humidity, light_level, water_tank_level, timestamp. Percentages are 0–100, temperature -10–60 Celsius, and timestamp must include timezone and fall within five minutes of the server clock. Unknown fields are rejected.

A retry keeps the same sample_id. Existing samples return duplicate=true without another database row or watering event. A new reading older than the latest one returns 409. A command response includes pump_on, absolute pump_until, target_moisture and server_time. The device must not extend a command by replaying a response.

Example sensor JSON is in sample_data/reading.json; replace its ID, sample ID and timestamp before sending. External Python and optional ESP32 clients remain separate from the built-in cloud simulator.
