# Verification results

Verification date: **26 September 2026**. Local environment: Windows, Python 3.14, Chrome headless and SQLite. Deployment targets use Python 3.12+ and Node 22+. Dependency versions are pinned in requirements.txt and frontend/package-lock.json.

## Executed checks

- **52 automated backend/simulator/public-account tests passed.** See test-results.xml and tests/ for individual cases.
- **React production build passed** using Vite 6.4.3. The restricted verification environment required `npm run build -- --configLoader native`; ordinary machines can use `npm run build`.
- **Frontend dependency audit: zero known vulnerabilities** at verification time. This is an npm audit result, not a security certification or a Python dependency audit.
- **Browser checks passed:** sign-in, overview, analytics, saving care settings, alerts, mobile layout at 390 px and absence of browser JavaScript errors.
- **Running-app control checks passed:** manual watering button, stop button, automatic low-soil start, target-moisture stop and alert acknowledgement. The latest browser flow outcomes are in browser-actions.json.
- **Live multi-device simulation observed:** three devices posted readings and recorded automatic watering events. Seeded history remains explicitly labeled demo_seed.

## Public-release additions

The additional 19 cases cover signup and cookie sessions, normalized/duplicate emails, invalid email values, logout, isolated/expiring guests, recovery-code rotation and old-token rejection, invalid recovery, deletion, origin validation, shared request limits, virtual sensor controls, ownership, inactivity suspension, guest cleanup, external-device compatibility, page reload and registration disablement.

## Requested test matrix

| ID | Scenario and input | Expected result | Actual result | Status |
|---|---|---|---|---|
| T01 | Start simulator with valid credentials | Process generates/sends readings | Three-device run sends HTTP 200 samples | PASS live |
| T02 | Generate a virtual sample | Bounded, gradual environmental values | Trend/bounds assertions passed | PASS automated |
| T03 | Valid sensor JSON and device key | API accepts reading | 200 | PASS automated |
| T04 | Moisture 101, humidity 101 or invalid field range | Reject input | 422 across parameterized cases | PASS automated |
| T05 | Ingest valid reading | Store one row | Database row count 1 | PASS automated |
| T06 | Get latest for owner | Return latest sensor values | Moisture 55 returned | PASS automated |
| T07 | Query history | Chronological records | Stored record retrieved | PASS automated |
| T08 | Moisture above/equal threshold | Pump remains off | Pump off | PASS automated |
| T09 | Moisture 29 with threshold 30 | Detect dry condition | Low-soil alert and command | PASS automated |
| T10 | Dry, fresh, tank 80, no cooldown | Start automatic watering | Pump on; event recorded | PASS automated + live |
| T11 | Active virtual command | Moisture increases | Next sample rises | PASS automated + live |
| T12 | Reading reaches 46 against target 45 | Stop and record target result | Pump off, target_reached | PASS automated + live |
| T13 | Dry again within 60 seconds | Prevent second command | Event count stays one | PASS automated |
| T14 | Fresh moisture 40, manual duration 5/10 | Manual command accepted | Pump on; button works | PASS automated + browser |
| T15 | Low moisture and high temperature | Create condition alerts | Two alert records | PASS automated |
| T16 | Owner acknowledges open alert | Mark acknowledged | Updated status | PASS automated + browser |
| T17 | Last-seen age greater than 45 seconds | Offline alert and manual lockout | Offline false/409 verified | PASS automated + browser |
| T18 | Sign in and load overview | Display latest cards | Cards rendered with live readings | PASS browser |
| T19 | Load and switch historical charts | Render sensor history | Chart rendered; metric selector available | PASS browser |
| T20 | Inject database exception | Generic recoverable response | 503 | PASS automated |
| T21 | API returns 503 repeatedly | Retry then fail closed | Simulator returns no command | PASS automated |
| T22 | API fails twice then succeeds | Retry same sample ID | Third request succeeds; payload unchanged | PASS automated |
| T23 | Missing JWT/key or another owner | Deny protected resources | 401/404 | PASS automated |
| T24 | Save threshold 40 and disable auto | Persist settings; no auto start | Settings saved; pump off | PASS automated + browser |
| T25 | Create another device, wrong original key | Independent identity and profile | Herb threshold 35; wrong key 401 | PASS automated |

Additional tests cover maximum duration, low-tank stopping, command expiry, duplicate ingestion, out-of-order timestamps, hash omission, overwatering guard and login throttling.

## Not executed

Hosted cloud deployment, PostgreSQL integration under load, Docker image execution, GitHub Actions on a remote repository, ESP32 compilation/flashing, physical watering, cross-browser accessibility audit, fleet-scale throughput and measured water savings. No screenshots or narrative represent these as completed.

## Reproduce

Run `python -m pytest -q --junitxml=reports/test-results.xml` in an installed environment. Run `npm ci`, `npm run build` and `npm audit` in frontend. Start the backend as in README; its virtual sensors run automatically, then exercise the recorded UI steps. Test assertions isolate their SQLite database from the actual demo database. Browser screenshots show synthetic data only.

