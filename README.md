# Smart QR

A Django service for company-managed, stable-URL digital business cards. V1 bills **R80 per active person per month**; deactivated cards expose no contact details.

## Local setup

Prerequisites: Python 3.11+, PostgreSQL 15+ (SQLite is the development fallback), and system build tools.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
createdb smartqr
export DATABASE_URL=postgresql://localhost/smartqr
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_sample
python manage.py runserver
```

The superuser is the development dashboard login at `/admin/login/`; no default password or real customer data is supplied. Run tests with `python manage.py test` and checks with `python manage.py check`.

## Environment

| Variable | Purpose / default |
|---|---|
| `SECRET_KEY` | Required strong random value in production; unsafe local fallback |
| `DEBUG` | `true` locally; set `false` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins |
| `DATABASE_URL` | PostgreSQL URL; local SQLite fallback |
| `PUBLIC_BASE_URL` | Canonical HTTPS origin encoded into every QR |
| `SECURE_COOKIES` | Secure session/CSRF cookies; defaults on outside debug |
| `SECURE_SSL_REDIRECT` | Set `true` when the platform forwards HTTPS correctly |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials |
| `AWS_STORAGE_BUCKET_NAME` | Enables object media storage when `DEBUG=false` |
| `AWS_S3_ENDPOINT_URL` | S3-compatible endpoint (AWS, R2, Spaces, etc.) |
| `AWS_S3_REGION_NAME` | Bucket region |
| `AWS_S3_CUSTOM_DOMAIN` | Optional CDN/public media domain |
| `AWS_QUERYSTRING_AUTH` | Signed media URLs; default `false` |
| `PORT` | Gunicorn port; Railway provides it |

Development uploads use `media/`. Production uploads require durable S3-compatible storage: ephemeral Railway disks must not hold customer images. Ensure the bucket CORS/public policy matches the chosen signed-URL setting.

## Railway deployment

Create a service from this repository and add Railway PostgreSQL. Railway supplies `DATABASE_URL`; configure the production variables above, particularly `SECRET_KEY`, `DEBUG=false`, host/origin values, canonical `PUBLIC_BASE_URL`, and object-storage credentials. The `Procfile`/`railway.json` start command applies migrations before Gunicorn starts, while WhiteNoise serves collected static assets. Run `python manage.py collectstatic --noinput` during build (or set it as a build command). The platform probes `/health/`.

V1 defaults are UUID public routes, immutable QR targets, local media only in development, R80 active-card billing, South African locale/timezone, and staff-only management. Back up PostgreSQL and the object bucket independently.
