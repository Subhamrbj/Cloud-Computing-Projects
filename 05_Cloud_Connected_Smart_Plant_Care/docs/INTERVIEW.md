# Interview preparation

These answers describe the supplied implementation honestly. Update cloud and hardware statements only after you personally complete those steps.

1. **Explain your project.**

   Verdant is a cloud-ready plant monitoring and watering application. A Python simulator behaves like an IoT sensor and sends soil moisture, temperature, humidity, light and tank readings to FastAPI. The backend stores data and applies plant-specific watering rules. A React dashboard shows history, alerts and controls. I can demonstrate the complete virtual cycle locally without buying hardware; cloud deployment files and an optional ESP32 prototype are included.

2. **Why use cloud computing for this problem?**

   Centralized storage lets the dashboard access the same plant state from different locations. Managed hosting and databases reduce infrastructure work and create a path to multiple devices and users. In the local demo, those roles run on one laptop; deploying the container with PostgreSQL demonstrates the remote version. I would not claim a cloud deployment until I verify a live URL.

3. **How does an IoT reading reach the dashboard?**

   A device posts JSON with its API key and unique sample ID. The backend verifies the key, validates ranges and timestamps, writes the sample and computes alerts and watering decisions. The dashboard polls authenticated endpoints every three seconds. This is near-real-time polling, not a WebSocket stream.

4. **How is the simulation more useful than random numbers?**

   Soil dries over time and rises after a pump command. Temperature and humidity vary smoothly, and light follows a cycle. This creates a repeatable control loop rather than disconnected random values. Accelerated mode compresses drying time for a short demo; it is not a calibrated biological model.

5. **How do you prevent overwatering?**

   Automatic and manual starts use common checks: fresh telemetry, enough tank water, soil below the target, no active command and a completed cooldown. Commands have absolute expiry and a maximum duration. The device also enforces a local cutoff. A command record does not prove actual water delivery, so real hardware needs feedback and physical safeguards.

6. **Why REST here, and when would you use MQTT?**

   REST is straightforward to test and works well for a small virtual fleet. MQTT offers lightweight publish/subscribe messaging, broker-managed connections and device topic routing for larger deployments. I would add a broker and durable queue when device scale or intermittent connectivity justifies the extra infrastructure. MQTT is described as an extension, not part of this release.

7. **How is the database organized?**

   A user owns devices, and a device owns readings, watering events and alerts. The device/timestamp index supports history queries. A unique device/sample key makes retries idempotent. SQLite gives a simple local start, while SQLAlchemy supports PostgreSQL for persistent cloud use. A production version would add migrations, retention and time partitions.

8. **How do you protect the API?**

   Passwords are scrypt-hashed. User JWTs expire, and resource queries enforce ownership. Device keys are hashed separately and scoped to one device. The application validates input and provides a basic rate limiter. HTTPS and database TLS protect cloud transport. Managed identity, key rotation and a shared gateway limiter are later hardening steps.

9. **What happens during failures or duplicate messages?**

   The simulator times out, retries a sample with the same ID and stops its virtual pump on persistent failure. Duplicate samples return the current bounded command without creating another event. Invalid or older samples are rejected. Database failures return 503, and missing heartbeats generate offline alerts while the host is running. Failed readings are not durably buffered in this version.

10. **How would you deploy and scale it?**

    For a student demo, I would deploy the Docker container on Render, connect managed PostgreSQL, provision credentials privately and verify telemetry over HTTPS. For a large fleet, I would add an IoT gateway, queue, stateless consumers, shared scheduling, managed identity, time-series retention and monitoring. The included local test evidence does not establish large-scale throughput or production availability.
