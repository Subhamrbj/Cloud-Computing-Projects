# Cloud-Computing-Projects

A collection of practical cloud computing projects, with source code, repeatable local setup, screenshots, and notes on how each application can be connected to cloud services.

## Projects

| No. | Project | Stack | What it demonstrates |
| --- | --- | --- | --- |
| 01 | [Daywell — Personal Diet Planner](01_Personal_Diet_Planner/README.md) | React, Vite, FastAPI, SQLAlchemy, SQLite | Accounts, profile-based meal plans, private file storage, a daily tracker, REST APIs, tests, and optional PostgreSQL/S3/AI adapters |

### Project 01: Daywell

![Daywell overview with a saved plan and demo intake](01_Personal_Diet_Planner/Screenshots/04_Overview.png)

The [project README](01_Personal_Diet_Planner/README.md) has setup instructions, feature details, architecture, limitations, and a screenshot gallery. See all four numbered images in [Screenshots](01_Personal_Diet_Planner/Screenshots/).

## Repository layout

```text
Cloud-Computing-Projects/
├── README.md
├── .github/workflows/ci.yml
└── 01_Personal_Diet_Planner/
    ├── README.md
    ├── Screenshots/        Numbered screenshots of the local demo
    ├── backend/            FastAPI application and tests
    ├── frontend/           React/Vite application
    ├── docs/               Cloud concept map and deployment guide
    ├── .env.example
    └── docker-compose.yml
```

To run Daywell, open `01_Personal_Diet_Planner` in VS Code and follow its [local setup guide](01_Personal_Diet_Planner/README.md#run-locally). The screenshots use synthetic demo data. The cloud database, S3-compatible storage, and live AI provider are **optional configurations**, not services claimed to be running in these screenshots.
