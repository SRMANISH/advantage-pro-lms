# Advantage Pro LMS

Internal, batch-centric Learning Management System for Advantage Pro (Vectra Technosoft).

- **Backend:** Django + Django REST Framework, PostgreSQL
- **Frontend:** React + Vite + TypeScript, Tailwind (light-blue & white theme)
- **Hosting:** Hostinger (integrated later) — built portable via swappable adapters

See [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the architecture & module roadmap, and
[`docs/DESIGN_PLAN.md`](docs/DESIGN_PLAN.md) for the UI/UX design.

## Repository layout

```
backend/    Django + DRF API (config, core, accounts, audit, …)
frontend/   React + Vite + TS app (design-system, features, …)
docs/        Build & design plans, ADRs
```

## Local development

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements-dev.txt
cp .env.example .env            # adjust DATABASE_URL for PostgreSQL when ready
python manage.py migrate
python manage.py seed_demo   # optional: one active account per role (password: Demo!passLMS1)
python manage.py runserver
```
Without a `DATABASE_URL`, the backend falls back to a local SQLite file for convenience.
PostgreSQL is the production database; set `DATABASE_URL=postgres://…` to use it.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Full stack via Docker (PostgreSQL + API)
```bash
docker compose up --build
```

## Quality gates
- Backend: `ruff`, `black`, `mypy`, `pytest`
- Frontend: `eslint`, `prettier`, `tsc`, `vitest`
