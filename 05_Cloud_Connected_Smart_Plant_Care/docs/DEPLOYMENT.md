# Deployment guide

The package is deployable; it has not been deployed to an external cloud account during preparation. You need your own provider account, database URL and generated secrets. Provider terms and pricing can change; check the linked official pages before selecting a plan.

## Student route: Render and Supabase PostgreSQL

1. Upload the source to a standalone GitHub repository, or set the service root directory to this project folder inside your existing repository. See PORTFOLIO.md for both layouts.
2. Create a Supabase project. Open **Connect** and copy its PostgreSQL **session pooler** connection string. Use the provider's current host/user/port values; do not copy example credentials. URL-encode reserved characters in the password. Session pooling is appropriate for this long-running SQLAlchemy app.
3. Set `DATABASE_URL` privately to `postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require`. For server identity verification, download the provider CA and configure `sslmode=verify-full&sslrootcert=/path/to/ca.crt` in the deployed environment. Do not commit a real connection string.
4. Provision the database explicitly from a local terminal: set DATABASE_URL to the cloud connection URL, then run `python -m scripts.setup_demo`. The schema and a new owner/devices will be created in that target database. Use a fresh local working folder if you already have a local demo to avoid overwriting a credentials file. `.demo-credentials.json` belongs to the database just provisioned. Back it up privately.
5. On Render choose **New Web Service**, connect the repository and select the Docker runtime. Alternatively, use the included `render.yaml` blueprint for a standalone repository. Set the project root when deploying from a subfolder. The Dockerfile builds React and serves it through FastAPI.
6. Set `DATABASE_URL` privately in the Render environment and generate a random `JWT_SECRET` of at least 32 characters. The blueprint can generate the signing secret. Keep a single service instance for this educational implementation.
7. Deploy. Render supplies PORT; the container binds 0.0.0.0. Set health check path `/api/health`. Do not use SQLite on an ephemeral cloud filesystem.
8. Open the provided HTTPS URL and sign in with the credentials from cloud provisioning. Start your local simulator with `python -m sensor_simulator.simulator --all --accelerated --url https://YOUR-SERVICE.onrender.com`, using that cloud database's local credentials file.
9. Confirm live telemetry, automatic watering, settings persistence after refresh, rejected anonymous access, history after application restart and device offline alerts while the service is awake. Capture the actual hosted URL and provider dashboard only after these checks pass.
10. Review provider logs and database usage. Keep secrets in environment settings. Configure backups and spending limits before extending the demo.

The single backend serves React on the same HTTPS origin, avoiding cross-origin identity configuration. Authentication is implemented in the backend with scrypt/JWT; this project does not use Supabase Auth or expose Supabase database credentials to React. Use a dedicated least-privilege PostgreSQL application role for serious deployments. Supabase's public Data API is not needed; restrict/disable it for these application tables or protect exposed schemas appropriately.

### Free hosting caveats

Render free web services may spin down when idle, so first requests can be slow and the in-process watchdog is paused while asleep. Do not rely on that plan for unattended irrigation or continuous monitoring. Free Render PostgreSQL expires after 30 days according to its current documentation, so this guide uses a separately managed database instead. Review Supabase's current free-plan quotas, pausing rules and backup availability. Neither provider is guaranteed to remain free indefinitely.

Official references reviewed 26 September 2026:
- [Render free deployment limitations](https://render.com/docs/free)
- [Render service types](https://render.com/docs/service-types)
- [Render deployments](https://render.com/docs/deploys)
- [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)

## Local Docker plus PostgreSQL

Docker is optional and was not available in the verification environment. The configuration is supplied but this path remains unexecuted.

Set `JWT_SECRET` and an alphanumeric random `POSTGRES_PASSWORD` in a local `.env` (URL-special characters need encoding in DATABASE_URL). Then:

```bash
docker compose up --build -d
docker compose exec app python -m scripts.setup_demo
docker compose cp app:/app/.demo-credentials.json .demo-credentials.json
python -m sensor_simulator.simulator --all --accelerated
```

Open localhost:8000. The database is stored in the `plant-data` Docker volume. The credentials file remains private. For shutdown use `docker compose down`; do not add `-v` unless you intend to delete database contents. Repeat provisioning only if this is a new database.

## Enterprise route

See the AWS architecture in ARCHITECTURE.md. Replace device-key HTTP ingress with AWS IoT Core certificates or an API Gateway authorizer, buffer messages with SQS/Kinesis, execute idempotent Lambda consumers, store device state in DynamoDB and history in a suitable managed time-series database, publish notifications through SNS, host React on S3/CloudFront, and monitor with CloudWatch. Use Cognito or equivalent managed user identity. These require additional infrastructure code and service integration; the package does not claim a deployable AWS stack.

Before autoscaling: remove the per-process limiter, move heartbeat checks into a shared scheduled job, adopt durable command acknowledgements, add migrations and implement bounded retention. Database row locks help serialize commands in PostgreSQL, but they do not make the entire educational service a validated fleet platform.
