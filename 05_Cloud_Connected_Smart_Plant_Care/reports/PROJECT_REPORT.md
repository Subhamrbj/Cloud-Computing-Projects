# Cloud Connected Smart Plant Care and Watering System

## Abstract

Verdant is a hardware-free implementation of a plant telemetry and irrigation-control application. A Python simulator generates environmental trends and receives bounded watering commands from a FastAPI backend. Persistent sensor history, configurable rules, owner-scoped access, alerts and a React dashboard form an end-to-end demonstration of IoT-to-cloud application design. The delivered system is verified locally. PostgreSQL and container deployment configurations provide a cloud path; actual hosted deployment and physical hardware validation remain separate activities.

## Introduction and problem statement

Manual watering often depends on memory and a fixed routine rather than observed soil conditions. Changes in temperature, light and available water can go unnoticed. A connected application can record conditions, apply consistent rules and make plant state visible remotely. For a cloud-computing student, physical sensors should not block learning API design, identity, persistence, automation and delivery.

## Objectives

The project aims to demonstrate a realistic virtual sensor, authenticated telemetry ingestion, durable history, configurable irrigation decisions, a usable monitoring interface, alert lifecycles and failure-aware operation. The deliverable also includes deployment instructions, repeatable tests and public portfolio material that distinguishes verified functionality from planned extensions.

## Existing and proposed systems

A manual routine has little historical evidence and limited remote visibility. A simple sensor-only prototype improves measurement but can leave identity, persistence and remote access unaddressed. Verdant separates device simulation, API processing, storage and user interaction. The same contract can accept an ESP32 client after hardware validation, while the cloud application's core remains unchanged.

## Industry relevance

The architectural pattern applies to greenhouses, nurseries, smart homes, precision irrigation, vertical farms, hydroponics, commercial landscapes and environmental monitoring. Centralized records and early alerts can improve care consistency and diagnosis. This project does not measure water savings or agricultural outcomes; such claims would require real trials, calibrated sensors and a suitable baseline.

## Cloud computing and IoT concepts

The application demonstrates device identity, REST communication, time-series storage, event-triggered decisions and remote interfaces. Container hosting is the PaaS deployment model; managed PostgreSQL supplies persistent cloud data. JWT authorization governs users, while separate keys govern sensors. Health checks, logs, bounded retries and CI support operations. Serverless functions, API gateways and MQTT appear in the enterprise extension design rather than the implemented local runtime. The complete concept mapping is in `docs/ARCHITECTURE.md`.

## Technology stack and architecture

React and Vite provide the interface. FastAPI supplies typed endpoints and OpenAPI documentation. SQLAlchemy maps the five principal entities onto SQLite locally or PostgreSQL remotely. The simulator uses HTTPX and an internal virtual plant state. Docker assembles the frontend and backend into one artifact so that the browser and API share an origin. A GitHub Actions workflow runs tests and builds the interface.

The workflow is: virtual plant → simulated measurement → authenticated ingestion → validated database record → watering/alert rules → expiry-bounded command → simulated moisture recovery → dashboard update. The server and device both enforce limits. Users can select plants, adjust thresholds, inspect alerts and issue manual requests within the same constraints.

## Sensor simulation

The simulator starts from a moisture level, decreases it with elapsed simulation time and increases it while a valid pump command is active. Temperature and humidity change smoothly; light follows a periodic pattern. Tank contents decrease during watering. A configurable accelerated mode makes the threshold cycle visible within minutes. This is synthetic test data rather than a calibrated physical or botanical model. Offline mode prints readings without a network service.

Every sample carries a UUID and UTC timestamp. Retries preserve the UUID, and the API rejects duplicate insertion. Requests time out and retry with exponential delays up to four attempts. When the connection remains unavailable, the virtual pump is stopped and future samples are generated afresh.

## Database design

Users own devices; devices own sensor readings, watering events and alerts. User email is unique. Device IDs and API-key hashes bind telemetry to registered identities. The reading table has a device/time index and a unique device/sample pair. Watering events record trigger, duration, starting moisture and observed ending moisture where available. Alerts store severity, status and resolution time. Server receipt time tracks heartbeat independently of the device's supplied timestamp.

## REST API

The application implements all primary endpoints from the brief: sensor ingestion, device listing/creation/detail, latest data, historical data, threshold updates, manual watering, watering history, alert listing and acknowledgement. Login, readiness, emergency stop and device command polling are additional endpoints. User resources require a bearer JWT and enforce ownership. Sensor routes require a device key. Invalid input, missing identity, conflicts and storage failure use distinct HTTP status codes. `docs/API.md` and the live `/docs` page specify the contracts.

## Watering algorithm

An automatic request is considered when measured soil moisture is below the selected threshold. It proceeds only if telemetry is recent, tank level exceeds 15%, a command is not already active and the 60-second cooldown has ended. The default command lasts ten seconds; API validation permits only one to fifteen seconds. Target moisture is the configured threshold plus fifteen percentage points. Readings at target or a low tank stop the command early. A watchdog reconciles expiry and offline state. Manual requests use the same safeguards.

Plant profiles supply different starting thresholds: succulent 20%, tomato 40%, herb 35% and indoor 30%. These values demonstrate configurability. They are not universal care recommendations, and real deployments must calibrate thresholds for plant, soil and sensor conditions.

## Dashboard

The interface presents a garden collection, device status, four environmental cards, history charts, pump state, tank level and watering journal. Overview provides operational context; Analytics exposes recent-window averages and extrema; Alerts supports acknowledgement; Settings controls threshold and automatic care. Layouts adapt to mobile widths. In-memory authentication avoids persisting bearer tokens in browser storage. Errors and unavailable devices are surfaced instead of silently presenting fabricated live success.

## Alerts and device monitoring

Low moisture, high temperature, low tank and stale heartbeat conditions produce persistent alerts. Repeated unhealthy readings reuse the active condition rather than creating unlimited duplicates. Acknowledgement records review without resolving the underlying problem; healthy readings resolve it. If more than 45 seconds pass without telemetry, the device is offline. The in-process watchdog runs every five seconds while the host is awake. Sleeping free hosting tiers cannot provide continuous background monitoring.

## Analytics

The dashboard calculates average/minimum/maximum moisture, average temperature/humidity, recent watering count and today's count from loaded records. Heartbeat coverage is the proportion of recent inter-sample gaps at or below the timeout; it is not measured cloud availability. The displayed history is deliberately bounded to 150 samples and 100 events, so metrics should not be described as lifetime totals. Estimated water consumption is omitted because no calibrated pump flow rate is provided.

## Cloud deployment

The student deployment combines one Docker web service with managed PostgreSQL and environment-managed secrets. React is served by FastAPI on the same HTTPS origin. Explicit local provisioning can initialize the cloud schema and owner. The Render blueprint and Dockerfile are included, alongside verified official documentation links and instructions for provider limitations. An enterprise design maps ingestion, queues, functions, storage and notifications to AWS, with Azure/GCP alternatives. These configurations are not evidence of an already running cloud deployment.

## Testing and results

The test suite covers authentication, owner isolation, storage, history, sensor validation, threshold boundaries, automatic/manual watering, target stopping, duration expiry, tank safety, cooldown, alert lifecycle, heartbeat failure, deduplication, out-of-order readings, device keys, simulator trends, retries, rate limits and storage exceptions. Browser checks cover sign-in, live dashboard rendering, analytics, care settings and mobile layout. Exact executed results, counts and limitations are maintained in `reports/TEST_RESULTS.md` and supporting evidence files.

## Security

Controls include scrypt password hashes, expiring signed JWTs, hashed per-device keys, owner-restricted database queries, schema validation, limited history reads and a basic per-process rate limiter. Cloud transport requires HTTPS and configured database TLS. Secrets, databases and generated credentials are excluded from public packages. Production extensions include managed identity/MFA, key rotation, durable command acknowledgements, shared limits, least-privilege roles and a formal migration process.

## Failure handling

Network failures trigger bounded retries and a local virtual cutoff. Invalid payloads are rejected without creating telemetry. Duplicate samples do not create duplicate watering events. Storage failures return a generic 503 response, avoiding connection-string leakage. Offline devices become visible through stale-heartbeat state. The event log records requested commands rather than verified physical delivery, which is a key distinction for real actuator systems.

## Scalability

One API process suits the demonstration. Larger deployments need connection pooling, a distributed rate limiter, dedicated heartbeat scheduling, a durable queue, stateless consumers, indexed/partitioned history and retention. At one reading per minute, one thousand devices generate approximately 1.44 million readings daily. This arithmetic motivates retention and batching but does not prove tested capacity. No fleet-scale throughput or availability claim is made.

## Advantages and limitations

The project is executable without hardware, separates responsibilities, uses a consistent API across local/cloud configurations and includes proof-oriented documentation. Limitations include synthetic sensing, command-only actuator records, single-process local operation, no durable offline backlog, no scheduled calendar watering, no push/SMS delivery and no measured water usage. The optional firmware requires compilation and physical testing; Docker/PostgreSQL/cloud paths require validation in an environment with those services.

## Future scope

Future work includes weather-aware decisions, additional sensors, real calibration, managed user identity, device provisioning/rotation, execution acknowledgements, queue-based ingestion, automated database migrations, scheduled care, retention and mobile notifications. Predictive watering could follow after collecting a representative dataset and comparing an ML model with a strong rule-based baseline. A model trained only on this synthetic data should not be claimed to predict real plant needs.

## Conclusion

Verdant demonstrates a complete local IoT-to-cloud application workflow with virtual sensors, persistent data, constrained automation and a usable dashboard. Its deployable structure provides a practical route to remote hosting, while the evidence and documentation clearly separate verified results from future infrastructure and hardware validation.
