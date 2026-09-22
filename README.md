# Pikabora Backend v0.2

Pregnancy-first nutrition intelligence API for Kenya, Nigeria and Senegal/WAFCT.

## What is implemented
- Country-aware meal recommendation engine and clinical safety override.
- Persistent user state, recommendation audit logs and preparation feedback.
- PostgreSQL production configuration with SQLite fallback for local development/tests.
- Food search/alias endpoint.
- Admin pilot metrics endpoint with optional `X-Admin-Key` protection.
- Docker and Docker Compose deployment.
- OpenAPI/Swagger automatically exposed by FastAPI at `/docs` when running.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload
```

## Run with PostgreSQL
Copy `.env.example` values into your deployment secrets, change all default passwords/keys, then:
```bash
docker compose up --build
```

## Main endpoints
- `GET /health`
- `GET /foods/search?country=KE&q=sukuma`
- `POST /nutrition/recommend`
- `POST /nutrition/feedback`
- `GET /users/{user_state_id}/state`
- `GET /admin/metrics`

## Safety/data boundary
Pikabora is nutrition decision support, not antenatal or clinical care. Clinical flags override ordinary meal optimisation. Food recommendations never replace prescribed/routine ANC supplements. Quantitative nutrition output remains gated unless portion and food-source inputs are verified.

## Next production work
Add WhatsApp provider webhook, authentication/consent, database migrations, encrypted secrets, rate limiting, observability, deletion/retention workflows, expanded verified food aliases, and nutritionist-reviewed regression fixtures before a live maternal-health pilot.
