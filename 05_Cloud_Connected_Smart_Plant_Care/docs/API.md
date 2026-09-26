# REST API reference

Open `/docs` for executable OpenAPI documentation. Errors have `{"detail":"message"}` or FastAPI validation details. Invalid/missing fields return 422; unauthenticated calls 401; a device outside the authenticated owner's scope 404; watering conflicts 409; rate limits 429; storage failure 503. Successful requests return 200 except device creation (201).

## Authentication

`POST /api/auth/login` accepts `{"email":"your-email","password":"your-generated-password"}` and returns `access_token`, `token_type`, `name`, `expires_in`. Use `Authorization: Bearer <access_token>` for owner routes. Tokens last one hour and are held only in browser memory. Reloading requires signing in again.

Provision the initial owner through `python -m scripts.setup_demo`. There is no anonymous self-registration endpoint. Device ingestion and command polling use `X-Device-Key`, never the user JWT.

| Method | Endpoint | Authentication | Request / response |
|---|---|---|---|
| GET | `/api/health` | None | Database readiness, version |
| POST | `/api/auth/login` | Email/password | Login body → JWT |
| GET | `/api/devices` | User | Owned devices, latest values, online and pump state |
| POST | `/api/devices` | User | Name/profile/location → device + one-time plaintext key |
| GET | `/api/devices/{id}` | User | Selected device and current state |
| GET | `/api/devices/{id}/latest` | User | Latest reading; 404 before first sample |
| GET | `/api/devices/{id}/history` | User | `limit=1..1000`, optional Unix `before`; chronological array |
| PUT | `/api/devices/{id}/threshold` | User | `moisture_threshold` 5..80 and `auto_water` boolean |
| POST | `/api/devices/{id}/water` | User | `{"duration":10}`; integer 1..15; bounded command |
| POST | `/api/devices/{id}/stop` | User | No body required; stops current command |
| GET | `/api/devices/{id}/watering-history` | User | Latest 100 command records |
| GET | `/api/alerts` | User | Latest 100 owner-scoped alerts |
| PUT | `/api/alerts/{id}/acknowledge` | User | No body; updated alert |
| POST | `/api/sensors/data` | Device key | Sensor JSON → duplicate flag + bounded command |
| GET | `/api/devices/{id}/command` | Device key | Current command; does not extend expiry |

## Sensor request

```json
{
  "device_id": "PLANT-001",
  "sample_id": "unique-id-for-this-sample",
  "soil_moisture": 29,
  "temperature": 29.4,
  "humidity": 61,
  "light_level": 72,
  "water_tank_level": 80,
  "timestamp": "2026-09-26T05:00:00+00:00"
}
```

Replace the example timestamp with current UTC; timestamps must be timezone-aware and within five minutes of server time. Soil moisture, humidity, light and tank level are percentages in 0–100; temperature is Celsius in -10–60. Device ID binds the reading to one authenticated device. `sample_id` remains unchanged on retries; the unique constraint prevents duplicate records. Older-than-latest samples return 409 so stale measurements cannot trigger new watering. Unknown properties are rejected.

Response: `{"duplicate":false,"pump_on":true,"pump_until":<Unix seconds>,"target_moisture":45,"server_time":<Unix seconds>}`. The device computes remaining duration, caps it at 15 seconds and stops on failure. Repeated responses never create a new command duration. `pump_on` is requested state, not an independent physical actuator acknowledgement.

## Example device creation

`POST /api/devices` with `{"plant_name":"Kitchen basil","plant_type":"herb","location":"Kitchen"}`. Profiles: indoor, herb, tomato, succulent. The response contains a random device ID and key. Save the key immediately; later GET responses omit secrets and key hashes.

## History and errors

Page backward using `before` equal to the earliest timestamp in the previous response. Do not infer whole-day analytics from a limited page. Validation and ownership checks apply before writes. Retry transport errors, 429 and 5xx with exponential backoff; do not continually retry invalid data or invalid credentials. The simulator retries a sample four times, then drops it and returns to generating fresh readings. It does not maintain a durable offline replay queue.
