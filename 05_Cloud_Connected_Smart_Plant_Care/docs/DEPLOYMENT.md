# Publish a live app — beginner walkthrough

This guide keeps your existing React + FastAPI stack. **Render runs the application; Supabase stores accounts and garden history in PostgreSQL.** Visitors use one public HTTPS link and need no software installation.

Status: the code is deployable and verified locally. Your provider accounts have not been connected here, so there is no actual live URL yet. Never post a placeholder as a live demo.

## 1. Upload the source to GitHub

Extract the GitHub upload ZIP. Upload `05_Cloud_Connected_Smart_Plant_Care` into your existing `Cloud-Computing-Projects` repository. Include the hidden `.env.example`, `.gitignore` and configuration files. Read PORTFOLIO.md for the exact folder layout.

For a new standalone repository, upload the contents of that project folder at repository root. Do not upload only the ZIP itself.

## 2. Create the database

1. Open https://supabase.com and create/sign in to your own account. Keep passwords private.
2. Create a **new project dedicated to this app**. Choose a region near you and a strong database password. Review the plan's current price before accepting it.
3. Wait for provisioning, then open **Connect**. Select **Session pooler** and copy the PostgreSQL connection string. This avoids common IPv4 connectivity problems with direct connections.
4. Replace the password placeholder in that string with your database password. If the password contains special URL characters, URL-encode them; a generated alphanumeric password avoids that complication.
5. Add `?sslmode=require` if the URL has no query string, or `&sslmode=require` if it already has one. This encrypts the connection. Stronger certificate verification uses `sslmode=verify-full` with the provider CA file; see the official link below.

The app creates its tables in the **plantcare schema**, rather than Supabase's default public schema. Do not add plantcare to exposed Data API schemas. Database credentials are used only by FastAPI, never in the frontend. In Supabase's table editor, select the plantcare schema to view the app tables after deployment.

For a more serious deployment, provision a dedicated least-privilege database role and grant only the app schema permissions. The beginner path uses the project connection provided by Supabase, so protect that connection string carefully.

## 3. Create the web service on Render

1. Open https://render.com and sign in with your own GitHub account. Authorize only the repository access required for this deployment.
2. Choose **New → Web Service**, connect your repository and select your main branch.
3. If the project is inside your existing repository, set **Root Directory** to `05_Cloud_Connected_Smart_Plant_Care`. Leave Root Directory empty for a standalone repository.
4. Choose **Docker** as the runtime. The supplied Dockerfile builds the React dashboard and starts FastAPI. Keep a single instance for this educational release.
5. Give the service a descriptive name such as `cloud-smart-plant-care`. If unavailable, choose another available descriptive name; Render supplies the actual URL.
6. Choose a plan after reviewing its current price. The free web tier is suitable for a portfolio demo but can sleep when idle.

## 4. Add the environment settings

In the Render service's Environment section, add:

| Name | Value |
|---|---|
| DATABASE_URL | Your private Supabase session-pooler URL with TLS enabled |
| DATABASE_SCHEMA | `plantcare` |
| APP_ENV | `production` |
| JWT_SECRET | A new random string, at least 32 characters |
| ALLOW_REGISTRATION | `true` |
| MAX_PUBLIC_USERS | `500` |

Generate JWT_SECRET on your laptop with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, then paste the result privately into Render. Do not put it in GitHub, a screenshot or a LinkedIn post. Render sets PORT itself; no manual PORT setting is needed.

Set the service health-check path to `/api/health`. No manual database seed is necessary: startup creates missing tables, and each visitor creates their own garden through the app.

## 5. Deploy and verify

Click **Create Web Service / Deploy**. Wait until the dashboard says deployment succeeded. Open the actual HTTPS URL shown by Render.

In a private browser window, verify:

1. **Try interactive demo** opens three plants without a password.
2. Click **Simulate dry soil**. The pump starts if safeguards permit, moisture rises, and a watering record appears.
3. Create an account and save its recovery code. Change a threshold, refresh and confirm it remains saved.
4. Sign out and sign in again. Confirm the same garden returns.
5. Open another private session and confirm it gets a different garden.
6. Review `/api/health`, application logs and the plantcare schema in Supabase.

Only now copy that HTTPS address into your GitHub README and LinkedIn post. The source link is your actual GitHub repository or numbered project folder. The demo link and source link should be different destinations.

## Common fixes

| Symptom | What to check |
|---|---|
| Database connection failure | Session pooler host/user/port, password encoding and TLS query parameter |
| Missing tables | Correct DATABASE_URL and database-role permission to create the plantcare schema |
| “Production requires PostgreSQL” | DATABASE_URL must use PostgreSQL, not the local SQLite example |
| “Set JWT_SECRET…” | Replace the placeholder with a genuine random value |
| Login succeeds but session disappears | Use HTTPS and APP_ENV=production; check browser cookies |
| “Request origin not allowed” | Set PUBLIC_URL to the exact public HTTPS origin, with no path |
| Service returns 404 or build fails | Root Directory must contain Dockerfile, requirements.txt and frontend/ |
| First load is slow | A free Render service may be waking from sleep |
| Watering blocked | Read the displayed reason: cooldown, sufficient moisture, offline sensor or low tank |

## Railway alternative

The included railway.json supplies a Docker build and readiness check. Create a Railway project, add PostgreSQL, deploy this source as a Docker service and reference the database URL in DATABASE_URL. Set APP_ENV=production, DATABASE_SCHEMA=plantcare and a random JWT_SECRET. Generate a public domain. Use the same verification steps above. Review trial limits and recurring cost before committing to a plan.

## Local Docker option

Set JWT_SECRET and an alphanumeric POSTGRES_PASSWORD in your private .env, then run `docker compose up --build`. Open localhost:8000 and try a demo or create an account. No setup_demo command is needed. The database volume persists data. Use `docker compose down` without `-v` to retain it. Docker execution was not available in the preparation environment, so this path is supplied but not claimed as executed.

## Costs and operational limits

The app uses bounded data retention, per-IP database-backed request limits, a 12-plant account limit, a temporary demo cap and a configurable account cap. Virtual sensors pause after five minutes without a dashboard visit. Free hosting may sleep; database plans may pause inactive projects or limit storage. This is a portfolio platform, not a validated unattended irrigation controller.

The Render blueprint uses an externally supplied PostgreSQL URL. This avoids treating Render's time-limited free database as permanent storage. Never assume a service will remain free indefinitely; inspect the current provider terms and dashboards.

Official references checked during preparation:
- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/platform/ssl-enforcement
- https://docs.railway.com/guides/fastapi
- https://docs.railway.com/deployments/healthchecks
