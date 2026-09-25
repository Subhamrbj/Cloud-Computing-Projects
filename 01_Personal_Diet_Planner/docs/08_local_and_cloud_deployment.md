# Local and Cloud Deployment

## Local development

Follow the VS Code instructions in the root README. Register, save a profile, generate a plan, save/export it, upload a file, log intake, and verify the dashboard. `GET /health` should report `database: true` and `storage: true`.

## Student cloud configuration

1. Create a managed PostgreSQL database; obtain a TLS-enabled `postgresql+psycopg://...` URL. Restrict access to the API service.
2. Create a private S3-compatible bucket. For R2, supply its endpoint, bucket, region (`auto` where supported), and credentials using `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. Give the service identity only the object permissions it needs.
3. Deploy `backend/Dockerfile` on a platform that supports containers. Supply `APP_ENV=production`, a random 32+ character `SECRET_KEY`, `DATABASE_URL`, `STORAGE_BACKEND=s3`, `S3_BUCKET`, `S3_ENDPOINT_URL` as needed, `S3_REGION`, credentials, and `CORS_ORIGINS`. Set the health path to `/health`.
4. Build `frontend/` on a static host using `npm ci && npm run build`, publishing `dist/`. Set `VITE_API_URL` to the HTTPS backend origin at build time. Configure a fallback rewrite to `index.html` for client routes.
5. Verify registration, profile, plan saving, upload/download, and cross-account isolation with two test accounts. Check `/health` and platform logs. Enable database backups and HTTPS. Test the actual AI provider separately if configured.

These are deployment steps, not evidence of a live deployment. Free service limits, pricing, timeouts, and sleep behavior change; review the provider's current terms.

## AWS option

Serve the compiled frontend from a private S3 bucket through CloudFront. Build and push the backend image to ECR, run it on ECS Fargate behind an HTTPS load balancer, use RDS PostgreSQL and a private S3 bucket for user objects, and keep secrets in Secrets Manager. Put application and access logs in CloudWatch. Configure network rules, RDS backup retention, health checks and least-privilege task policies. GitHub Actions can build and test before a separate approved deployment workflow.

## Operations notes

- The backend calls `Base.metadata.create_all()` for an initial demo schema. For production schema changes, add Alembic migrations before changing tables.
- The storage adapter is selected at process startup. Moving existing objects or SQLite data to cloud requires a separate migration/export procedure.
- The in-memory rate limiter does not coordinate across replicas. Use an API gateway or Redis-backed limiter for distributed deployments.
- Objects are private. Back up both database and bucket, and test restoration together.
- Publish the deployment URL and date only after personally verifying the live application.
