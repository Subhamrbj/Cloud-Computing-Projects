# Optional browser regression check

Start the demo backend and simulator first. Use a fresh generated local credentials file. Install Playwright as a local test tool with `npm install --no-save --package-lock=false playwright` at the project root, then run `node scripts/browser_smoke.cjs`. Google Chrome must be installed. This script signs in, captures screenshots, saves and restores the first plant threshold, visits analytics/alerts, and checks mobile overflow and JavaScript errors. It expects the standard three seeded plants and uses localhost:8000. It is intended for a disposable demo database, not someone else's deployed garden.

The broader watering control checks are recorded in reports/browser-actions.json and covered by automated backend tests. No runtime credentials should be added to Git.
