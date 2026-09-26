# Public-use release 2.0

The former invented project name has been removed. The application uses the descriptive title **Cloud-Connected Smart Plant Care & Watering System** and the short interface label **Plant Care**.

## What changed

- Visitors can create an account and receive a private garden.
- A no-signup guest demo gives each visitor an isolated one-hour session.
- The hosted backend now runs virtual sensors automatically; visitors do not need a local Python client.
- Start/pause, dry-soil and tank-refill controls make the automation easy to demonstrate.
- HttpOnly cookie sessions survive reloads; recovery codes reset passwords and invalidate old JWTs.
- Account deletion removes owned records.
- Database-backed rate limits, quotas and retention bound the public portfolio service.
- Production requires PostgreSQL and uses a dedicated schema.
- Render and Railway configuration, updated tests and beginner deployment instructions are included.

## Verification boundary

Local automated tests, frontend builds and browser flows are verified. Hosted deployment requires access to the owner's hosting accounts and has not been performed. The example shortened link could not be inspected: the browser tool reported that access was declined. The pasted post was used for presentation guidance; no other person's identity, affiliations or deployment claims were copied.
