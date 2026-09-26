# Security and privacy

## Implemented

Users register private accounts with scrypt-hashed passwords. JWTs expire after one hour. Browser sessions use a necessary HttpOnly, SameSite=Lax cookie; production marks it Secure. The API can also accept a bearer token. Every protected request checks that the user still exists and the token's account version is current.

Registration returns a random recovery code once. Only its hash is stored. A valid code can reset the password, rotate the recovery code and increment the account version, invalidating previous JWTs. Email addresses are login identifiers, not verified addresses; no email provider or email reset flow is claimed.

Guest demos use independently created accounts with one-hour expiry. They cannot read or change another guest's or registered user's garden. Periodic cleanup removes expired guest data. Users can delete their registered account with password confirmation; deletion removes its devices, sensor records, virtual state, watering history and alerts.

Device keys are separately hashed and scoped to one externally connected device. Virtual plants accept only authenticated owner simulation controls, so external telemetry cannot silently take over their state. All user/device ownership checks run on the server.

Mutating browser requests reject unexpected Origin headers. Typed schemas validate input, sensor timestamps and ranges. Device/sample uniqueness rejects duplicate insertions. History is limited. Login, registration, guest creation, recovery and ingestion use database-backed fixed-window request counters; quotas limit accounts and plants. These are application-level controls, not a replacement for provider DDoS protection.

Production refuses SQLite to prevent accidental ephemeral storage. PostgreSQL uses a dedicated schema named plantcare by default, keeping application tables outside Supabase's default exposed public schema. Do not expose the plantcare schema through Supabase's Data API. Use a dedicated least-privilege role for deployments beyond a student portfolio.

Responses include frame, MIME, referrer, permissions and content-security headers. Production sends HSTS. HTTPS and database TLS must be configured at the hosting layer. Secrets never belong in frontend code, GitHub or screenshots.

## Retention

Raw readings older than seven days are removed, except the newest sample for each device. Completed watering events and resolved alerts are retained for 90 days. Expired guest accounts are removed on periodic cleanup, which runs only while the app is awake. Registered accounts remain until deletion. This is disclosed in the in-app privacy notice.

## Watering safeguards

The same freshness, tank, target, duration and cooldown checks govern manual and automatic starts. Commands have absolute expiry. Built-in virtual telemetry accounts for only the bounded active portion of a command; process downtime is not replayed as hours of watering. The optional physical device must independently time out and stop on failure. Server command state is not a physical actuation acknowledgement.

## Limits and future hardening

No email verification, MFA, passkeys, managed identity, device-key rotation UI, independent security audit or large-scale load test is claimed. Logout clears the browser cookie; previously copied bearer tokens remain valid until expiry or account recovery/deletion. Origin validation and same-site cookies mitigate browser cross-site requests, but reverse-proxy configuration should be reviewed before deployment.

The simulation watchdog is intended for one application process. PostgreSQL row locks coordinate device writes, but scaling the application requires a dedicated scheduler and tested concurrency. Platform downtime or sleeping free tiers interrupt background work. Passwords, recovery codes and DB URLs should never be logged.

The external Python simulator retries with timeout/backoff and preserves sample IDs. It drops persistently failed samples rather than keeping a durable offline queue. Database errors return a generic 503. Hardware, calibration and measured water savings remain outside the verified release.
