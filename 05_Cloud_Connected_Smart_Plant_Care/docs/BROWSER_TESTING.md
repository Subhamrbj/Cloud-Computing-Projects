# Browser verification

Start the local application on port 8000. From the project root, install the optional test tool with `npm install --no-save --package-lock=false playwright`, then run `node scripts/browser_smoke.cjs`. Google Chrome must be installed.

The script opens a private guest garden, verifies automatic watering, stop, settings, charts, alerts and mobile overflow, then creates a temporary account to verify manual watering, recovery and account deletion. It removes its own registered account and leaves its guest to expire. Use a disposable local database. No shared login or external sensor process is required. Screenshots and browser results are written to Screenshots/ and reports/.

The supplied browser-actions.json records the completed local run. Cloud deployment and physical hardware have not been tested.
