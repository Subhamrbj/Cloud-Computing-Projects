# Start here

**Verdant is a complete local virtual plant-care project with a cloud deployment path.**

1. Read README.md and install Python 3.12+ and Node 22+.
2. On Windows, run Start-Windows.ps1, or use the explicit README commands. The complete package includes frontend/dist, so a frontend rebuild is optional there.
3. Open the generated `.demo-credentials.json` privately and sign in at http://127.0.0.1:8000.
4. Start the sensor simulator in a second terminal using the command in README.
5. Read docs/PORTFOLIO.md for GitHub upload and LinkedIn copy.

The project report is reports/PROJECT_REPORT.md. Actual screenshots are in screenshots/. The cloud guide is docs/DEPLOYMENT.md. Everything runs with synthetic sensors; no physical equipment is required.

The GitHub-ready ZIP contains source, documentation, tests and screenshots without dependencies, secrets or local data. The complete ZIP also includes the compiled frontend and presentation assets. Neither ZIP includes Python/Node themselves or installed dependency folders; first-time installation requires internet.

Verified locally: backend tests, frontend build, browser pages, mobile layout and watering controls. Not verified: hosted cloud infrastructure, Docker/PostgreSQL execution or ESP32 hardware. These boundaries are detailed in reports/TEST_RESULTS.md.
