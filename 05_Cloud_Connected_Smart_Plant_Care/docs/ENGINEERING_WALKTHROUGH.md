# Engineering walkthrough

## Problem and working scope

Plant monitoring connects several concerns: device identity, unreliable telemetry, persistent history and decisions that must stop safely. This project implements that workflow with virtual devices, making it possible to exercise both normal and failure states without a hardware kit.

The working application includes isolated guest gardens, registered accounts, sensor charts, manual and automatic watering, alert acknowledgement, password recovery and account deletion. Sensors and pumps are simulated. The local release recorded 52 passing tests and browser verification; cloud and physical-device execution require separate validation.

## Follow one watering decision

1. A built-in virtual sensor advances its readings, or an external client submits authenticated telemetry.
2. The backend validates the values, identifies the device and stores the reading. External samples include an identifier so a retry does not insert a duplicate reading.
3. The rule engine checks moisture, freshness, tank level, cooldown and whether a command is already active.
4. An eligible command creates a watering event and an expiry time. The virtual sensor models moisture recovery while it is active.
5. Reaching the target, exhausting the tank, expiring the command or losing the heartbeat stops the watering state. The dashboard displays readings, alerts and the event journal.

Start with [watering_engine.py](../automation/watering_engine.py), then [services.py](../backend/services.py) and [public_service.py](../backend/public_service.py).

## Design decisions and tradeoffs

| Decision | Reason | Tradeoff or next step |
|---|---|---|
| Serve React and FastAPI from one deployment | One public origin simplifies sessions and initial deployment | Independent frontend scaling is deferred |
| Use SQLite locally and PostgreSQL for production mode | Local setup is accessible while hosted data survives application restarts | PostgreSQL integration and migration handling need deployment validation |
| Use per-device keys for external telemetry | Device ingestion does not require the owner's login token | Provisioning and key rotation need a fuller device-management workflow |
| Bound watering commands and reject stale readings | Failures should not leave a command running indefinitely | Real hardware still requires a tested local cutoff and calibrated sensors |
| Run virtual sensors in the backend | A visitor can use the demo without launching a separate process | Designed for a single application instance; background scheduling would need redesign for scale |
| Use separate temporary guest gardens | Visitors can explore controls without changing another person's garden | Expiring sessions and periodic cleanup are required |
| Use recovery codes rather than an email service | Password recovery works without an email provider | The user must retain the code; email ownership is not verified |

## Verification map

| Concern | Evidence |
|---|---|
| Authentication, account ownership, guest expiry and recovery | [test_public_app.py](../tests/test_public_app.py) |
| Telemetry validation, duplicate retries, cooldowns, tank limits and offline behavior | [test_system.py](../tests/test_system.py) |
| Signup, watering, recovery, settings and mobile layout | [Browser results](../reports/browser-actions.json), [reproducible browser check](BROWSER_TESTING.md) |
| Recorded local test outcomes and untested paths | [Test results](../reports/TEST_RESULTS.md) |
| Current tests and frontend build on GitHub | [Plant care workflow](../../.github/workflows/plant-care.yml) |

## Three-minute local walkthrough

Run the application using the [README](../README.md#quick-local-start), then:

1. Choose **Try interactive demo** and inspect the three plants.
2. Choose **Simulate dry soil** and observe automatic watering, then stop the command.
3. Open analytics and switch the sensor metric.
4. Change a care threshold, acknowledge an alert and pause a sensor to explore heartbeat failure.
5. Open the rule engine and tests to explain why a watering request may be rejected.

## Next validation milestones

- Deploy the web service with PostgreSQL and verify sessions, persistence and isolation over HTTPS.
- Introduce versioned database migrations before evolving a deployed schema.
- Validate a real ESP32 client, electrical controls and local pump cutoff independently of the cloud service.
- Measure load and storage behavior before increasing the public account or device limits.

See [architecture](ARCHITECTURE.md), [API](API.md), [security](SECURITY.md) and [deployment](DEPLOYMENT.md) for the implementation details.
