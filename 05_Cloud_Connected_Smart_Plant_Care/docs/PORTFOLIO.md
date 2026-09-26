# GitHub and LinkedIn publishing kit

## Choose your repository layout

Your reference screenshot shows a `Cloud-Computing-Projects` repository with numbered project folders. The GitHub upload ZIP follows that pattern: its project folder is named `05_Cloud_Connected_Smart_Plant_Care`. Extract the ZIP before uploading; uploading the ZIP alone makes the source difficult to browse.

### Existing Cloud-Computing-Projects repository

1. Extract the GitHub ZIP. Copy `05_Cloud_Connected_Smart_Plant_Care` into your local clone.
2. Copy the supplied `.github/workflows/plant-care.yml` into the repository-level `.github/workflows` folder. It is scoped to this project and does not replace existing workflows. Nested workflow files inside the project folder are only templates; GitHub runs workflows only at repository root.
3. Add this entry to your repository root README:

```markdown
### 05 — Cloud-Connected Smart Plant Care
Cloud-ready plant monitoring with virtual IoT sensors, authenticated APIs, automated watering, alerts, and a React dashboard.
[Explore the project](05_Cloud_Connected_Smart_Plant_Care/README.md)
```

4. From the root of your existing clone, review and publish:

```bash
git status
git add 05_Cloud_Connected_Smart_Plant_Care .github/workflows/plant-care.yml
git diff --cached --stat
git commit -m "Add Plant Care cloud-connected smart plant care project"
git push origin main
```

If using GitHub's web interface, open **Add file → Upload files** at repository root and drag in the extracted project folder. Check that `.env.example` and `.gitignore` are present; browsers may hide dotfiles in file pickers. Upload the workflow separately if the web flow cannot preserve its folder. Never upload `.env`, `.demo-credentials.json`, databases, `.venv`, `node_modules`, or runtime logs. The supplied GitHub ZIP excludes these.

### Standalone repository

Create an empty repository named `Cloud-Connected-Smart-Plant-Care`. Work inside the extracted project folder so its README is at the repository root:

```bash
git init
git add .
git diff --cached --stat
git commit -m "Initialize Plant Care smart plant cloud platform"
git branch -M main
git remote add origin https://github.com/Subhamrbj/Cloud-Connected-Smart-Plant-Care.git
git push -u origin main
```

Confirm the account/repository URL before using it. If an origin already exists, inspect it with `git remote -v`; do not overwrite unrelated repositories. For the standalone layout the project's own `.github/workflows/ci.yml` is in the correct root location.

**Repository description:** Cloud-connected plant monitoring and watering platform with simulated IoT sensors, authenticated REST APIs, persistent data storage, automatic irrigation rules and a React dashboard.

**Topics:** `cloud-computing`, `iot`, `smart-agriculture`, `python`, `fastapi`, `react`, `postgresql`, `rest-api`, `automation`, `smart-irrigation`, `sensor-data`, `cloud-monitoring`.

## LinkedIn post

Use the current post in [LINKEDIN_POST.md](LINKEDIN_POST.md). Add your real source URL after upload and a live URL only after deployment.

## Resume material

- Implemented a virtual IoT telemetry workflow using Python, FastAPI and SQLAlchemy, with timestamp validation, device authentication and idempotent sensor ingestion.
- Built a React monitoring dashboard with sensor trends, plant-specific watering controls, alert acknowledgement and device heartbeat status.
- Added automated tests for access control, watering safeguards and failure handling, plus Docker and PostgreSQL deployment configurations.

**Two-line project description:**
This cloud-ready plant care platform connecting simulated sensors to authenticated APIs, persistent storage and a React dashboard.
It demonstrates bounded watering automation, historical monitoring, alert lifecycles and repeatable local execution without physical hardware.

**Skills demonstrated:** Python, FastAPI, React, Vite, REST, JWT, scrypt, SQLAlchemy, SQLite, PostgreSQL integration, IoT simulation, fault handling, Docker configuration, CI and cloud architecture.

## Screenshot checklist

| Suggested filename | What it proves | Status in this package |
|---|---|---|
| 00_Login.png | Rendered sign-in page | Captured locally |
| 01_Dashboard.png | Running dashboard, sensor cards and chart | Captured locally |
| 02_Analytics.png | Recent-window analytics | Captured locally |
| 03_Care_Settings.png | Threshold and automatic mode controls | Captured locally |
| 04_Alerts.png | Alert page | Captured locally |
| 05_Mobile.png | Responsive mobile layout | Captured locally |
| 06_Automatic_Watering.png | Active virtual watering state | Capture supplied if verified during run |
| 07_Manual_Watering.png | Manual command and pump state | Capture supplied if verified during run |
| 08_Offline_Alert.png | Stale heartbeat alert | Capture supplied if verified during run |
| 09_Architecture.svg | Application data flow | Included diagram |
| 10_Cloud_Deployment.png | Provider deployment status | Capture after your own deployment |
| 11_Live_Application.png | Actual hosted HTTPS application | Capture after your own deployment |
| 12_GitHub_Repository.png | Uploaded code/README | Capture after upload |
| 13_GitHub_Commits.png | Real commit history | Capture after committing |

Also capture simulator logs, an authenticated sensor API request with the key hidden, database rows, dry-soil recovery and test output when presenting a walkthrough. Do not create fake cloud-console screenshots. The build/test evidence files supplement the screenshots without exposing credentials.

## Suggested development learning sequence

This is a study and iteration plan, not a fabricated account of past work. Create each commit only after you actually review, modify or validate that stage.

| Day | Files to study or improve | Functionality | Suggested genuine commit | Evidence to capture |
|---|---|---|---|---|
| 1 | docs/ARCHITECTURE.md | Trace data flow | Document plant cloud architecture | Diagram |
| 2 | sensor_simulator/ | Understand trend model | Refine virtual sensor trends | Simulator output |
| 3 | backend/app.py, schemas.py | Ingest/validate data | Extend sensor API validation | Redacted request/response |
| 4 | cloud/, backend/models.py | Persistent storage | Validate cloud database integration | Database row |
| 5 | automation/, services.py | Bounded watering | Verify watering safeguards | Pump on/off |
| 6 | plant_profiles.py | Threshold profiles | Refine plant care profiles | Settings |
| 7 | frontend/src/ | Dashboard state | Improve monitoring dashboard | Overview |
| 8 | backend/services.py | Alert lifecycle | Extend alert handling | Low-soil alert |
| 9 | frontend/src/main.jsx | Recent-window metrics | Add analytics improvement | Chart |
| 10 | backend/app.py | Heartbeat sweep | Verify offline detection | Offline alert |
| 11 | tests/ | Regression checks | Add project regression test | Test output |
| 12 | Dockerfile, render.yaml | Actual deployment | Deploy plant application | Hosted URL and provider status |
| 13 | README, reports/ | Explain verified results | Complete project documentation | Repository README |

## Three-minute demonstration

0:00 — Explain why a virtual device makes IoT-to-cloud development accessible.
0:25 — Open the interactive demo and show the three plants, sensor cards and history.
0:55 — Use Simulate dry soil and watch soil dry through a threshold.
1:25 — Show bounded pump activation, rising moisture and recorded event.
1:55 — Change a threshold, issue a permitted manual command and acknowledge an alert.
2:25 — Show tests, architecture, database configuration and deployment limitations.
2:50 — Explain the next step: real cloud verification or calibrated hardware.
