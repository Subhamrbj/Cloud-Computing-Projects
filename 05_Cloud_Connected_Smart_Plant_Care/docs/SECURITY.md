# Security and failure handling

## Implemented controls

People authenticate with email and an scrypt-hashed password. Expiring HMAC-signed JWTs authorize owner-scoped resources. The browser holds its token in memory, not localStorage. Device keys are random and stored only as SHA-256 hashes; compare operations use constant-time comparison. A key is scoped to one device and cannot invoke owner administration endpoints. The one-time creation response is the only API response that returns the plaintext key.

Inputs have strict schemas and ranges. Timestamp freshness and ordering prevent old readings from steering automation. Unique sample IDs make retrying a measurement idempotent. Database transactions and device row locks coordinate updates; the local SQLite mode additionally uses a process lock. Do not run multiple workers against SQLite.

API responses omit password/key hashes, logging avoids request credentials, history requests have limits and request bodies have a declared-size guard. Login is limited to 20 attempts/IP/minute; sensor ingress to 600 requests/IP/minute in one process. A real reverse proxy must add trusted client-IP handling and a distributed limiter. This guard is not a complete distributed denial-of-service defense.

Cloud HTTPS encrypts transport. Database TLS is configured through DATABASE_URL; verify-full plus the provider CA enables server identity verification. Encryption at rest and backups depend on provider settings; they are not properties of plain local SQLite. Secrets belong in ignored local files or provider secret stores. Do not expose a database superuser/password in frontend code. Use a dedicated application database role with only necessary schema/data access.

## Watering safety

All commands, including manual watering, require a recent reading, tank above 15%, soil below target, no active command and a 60-second cooldown. Duration is 1–15 seconds. Sensors implement their own expiry and failure cutoff. A stale device cannot be manually watered. The UI's stop control cancels the cloud command; a physical device must receive or independently expire it. Never rely exclusively on a browser or cloud watchdog to protect a real pump.

Public, unauthenticated watering endpoints would permit arbitrary actuation and potential flooding. This implementation requires ownership and validates each command. Still missing for production: MFA, refresh-token/session revocation, password reset, key rotation UI, formal audit export, durable execution acknowledgements and professional hardware validation.

## Failure matrix

| Failure | Implemented behavior | Remaining limitation |
|---|---|---|
| Internet/API unavailable | Timeout, four bounded retries, exponential backoff; virtual pump off on failure | No durable offline queue; failed samples may be dropped |
| Simulator stopped | Last-seen becomes stale; offline alert; command expires | Watchdog requires a running host |
| Database unavailable | API responds 503 with generic error; transaction rollback | External monitoring/backups must be configured |
| Invalid reading | 422; no sensor row/automation change | Physical calibration remains external |
| Duplicate sample | Existing record recognized; no new event | Deduplication keyed by device/sample ID |
| Out-of-order sample | 409; rejected for control safety | Historical backfill needs a separate future endpoint |
| Pump command response lost | Retry same sample; returned expiry does not extend | Command creation is not proof of delivery |
| Sensor tank low | New command blocked; active command stopped | Real tank sensor failure needs hardware fail-safe |
| Service restarted | Database retains records; command expiry reconciles | In-memory login limiter resets |

## Monitoring and operations

Monitor `/api/health`, logs, database latency, queue/failure metrics if added, and device heartbeat ages. Set cloud alerting for 5xx spikes and failed readiness checks. Never log JWTs, passwords, device keys or connection URLs. Data retention and export/deletion policies must be agreed before collecting non-demo user data. This release uses only synthetic sensor values.
