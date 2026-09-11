# Trackxpens API

Django REST API for the Trackxpens expense tracker. It includes email/password authentication, 90-day JWT sessions, PIN locking, onboarding, categories, budgets, expenses, period summaries, settings, and finance lessons.

## Local setup

Python 3.9+ is supported. The default database is SQLite so the API can run immediately.

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_lessons
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/`
Swagger docs: `http://127.0.0.1:8000/docs/`
OpenAPI schema: `http://127.0.0.1:8000/schema/`

## PostgreSQL

PostgreSQL is recommended for production. Copy `.env.example` to `.env`, start PostgreSQL, and set:

```env
DATABASE_URL=postgresql://trackxpens:trackxpens@localhost:5432/trackxpens
```

When using Docker Compose, keep the `DATABASE_URL` above in your host `.env`; the Compose file automatically changes the database host to `db` inside the web container.

With Docker, run `docker compose up --build`, then run migrations in the web container:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Main API flow

1. `POST /api/auth/register/`, then `POST /api/auth/login/` with `email` and `password`.
2. Save the returned access token as `Authorization: Bearer <token>`.
3. Complete `PUT /api/onboarding/` and `POST /api/pin/set/`.
4. Create categories, then budgets, then expenses. An expense must reference a budget belonging to the authenticated user.
5. Read `GET /api/summary/?period=day|week|month|year`.

Password reset sends through SMTP when `EMAIL_HOST` is configured, otherwise the reset email is printed to the development console. The frontend should provide the `user_id`, token, and new password to `/api/auth/password-reset/confirm/`.

The original `bytapi` project is FastAPI/MongoDB. This clone keeps its JWT, email reset, and onboarding concepts while using Django/PostgreSQL for the expense domain.
