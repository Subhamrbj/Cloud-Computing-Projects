# Cloud Concepts and Implementation Map

| Concept | Implementation | Local equivalent |
| --- | --- | --- |
| SaaS access | React frontend and authenticated FastAPI application | Vite and Uvicorn on localhost |
| PaaS backend | `backend/Dockerfile`, environment configuration | Container or local process |
| Managed relational database | `backend/app/db.py`, `models.py` with PostgreSQL URL | SQLite database |
| Object storage | `backend/app/storage.py` S3 adapter | Private local folder adapter |
| Stateless application | JWT authentication and external database/object data | API process with durable local disk |
| AI as a service | `backend/app/ai_engine.py` and response validator | Rule-based engine |
| Identity/authorization | `backend/app/auth.py`, per-user filters in `main.py` | Same logic locally |
| Continuous integration | `.github/workflows/ci.yml` | `pytest` and `npm run build` |
| Monitoring | `/health` checks DB and storage | Health check in local browser |
| Horizontal scaling | Database and S3 externalize application data | Not demonstrated by single local instance |

A cloud deployment must configure credentials, database, object storage, CORS, TLS, and a persistent signing key. Object paths include the user ID but remain private; file downloads pass through the API after ownership checks. Cloud provider pricing and free tiers should be reviewed at deployment time.
