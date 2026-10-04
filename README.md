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
| `MEDIA_ROOT` | Persistent upload directory; automatically uses `/data/media` when a Railway volume is mounted at `/data` |
| `SERVE_MEDIA` | Serve volume-backed uploads from Django; defaults to `true` unless object storage is enabled |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Optional S3 credentials instead of a volume |
| `AWS_STORAGE_BUCKET_NAME` | Enables object media storage when `DEBUG=false` |
| `AWS_S3_ENDPOINT_URL` | S3-compatible endpoint (AWS, R2, Spaces, etc.) |
| `AWS_S3_REGION_NAME` | Bucket region |
| `AWS_S3_CUSTOM_DOMAIN` | Optional CDN/public media domain |
| `AWS_QUERYSTRING_AUTH` | Signed media URLs; default `false` |

Development uploads use `media/`. In the Railway setup below, production uploads
are stored on a persistent application volume mounted at `/data`.

## Railway deployment (step by step)

The application needs two services in one Railway project: the **Smart-QR web
service** (this repository) and **PostgreSQL**. The `postgres-volume` shown under
PostgreSQL in Railway is the database's persistent disk; leave it attached to
PostgreSQL. Do **not** attach that volume to Smart-QR.

### 1. Add PostgreSQL and connect it

1. Open the Railway project, click **+ New**, choose **Database**, then choose
   **PostgreSQL**. If the Postgres service and its `postgres-volume` are already
   online, as in the screenshot, this step is complete.
2. Open the **Smart-QR** service, select **Variables**, click **+ New Variable**,
   and add a variable reference named `DATABASE_URL` that points to the
   PostgreSQL service's `DATABASE_URL`. A reference is preferable to copying the
   connection string because Railway keeps it in sync.
3. Do not expose the PostgreSQL service with a public domain. Smart-QR uses the
   private project connection supplied by `DATABASE_URL`.

### 2. Add the production variables

In **Smart-QR > Variables**, add the following (replace the example domain with
the real Railway or custom domain):

```text
SECRET_KEY=<a-long-random-secret>
DEBUG=false
ALLOWED_HOSTS=smart-qr-production.up.railway.app
CSRF_TRUSTED_ORIGINS=https://smart-qr-production.up.railway.app
PUBLIC_BASE_URL=https://smart-qr-production.up.railway.app
SECURE_COOKIES=true
SECURE_SSL_REDIRECT=true
```

Generate `SECRET_KEY` locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`ALLOWED_HOSTS` contains hostnames only (no `https://` or path), while
`CSRF_TRUSTED_ORIGINS` and `PUBLIC_BASE_URL` must include `https://`. For more
than one hostname, separate values with commas. Railway supplies the `PORT`
environment variable to the application; the start command uses it automatically
and falls back to `8000` for local use.

### 3. Attach the image volume

Profile photos and company logos must survive redeploys. Attach a **new, separate
volume** to the Smart-QR service; do not reuse or move the PostgreSQL volume.

1. Open the **Smart-QR** service in Railway.
2. Open **Variables**, click **+ New Volume** (or add a volume from the project
   canvas), and enter this exact mount path:

```text
/data
```

3. The application automatically detects the `/data` mount and stores uploads
   under `/data/media`. No media variables are required for this layout. You may
   still set these explicit Smart-QR service variables if you prefer:

```text
MEDIA_ROOT=/data/media
SERVE_MEDIA=true
```

The app creates the `media` subdirectory when files are uploaded and serves
those files at `/media/...`. Mounting the volume at `/data` keeps its contents
separate from application files replaced during a deployment. After saving the
volume and variables, redeploy Smart-QR.

The final layout is:

```text
Postgres service  -> postgres-volume (managed by the Postgres template)
Smart-QR service  -> separate volume mounted at /data
Uploaded images   -> /data/media
```

#### Optional: use object storage instead

S3-compatible object storage remains available as an alternative to the
Smart-QR volume. If using S3, do not create the Smart-QR volume and do not set
`SERVE_MEDIA=true`; instead add:

```text
AWS_ACCESS_KEY_ID=<bucket-access-key>
AWS_SECRET_ACCESS_KEY=<bucket-secret-key>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_ENDPOINT_URL=<provider-endpoint>
AWS_S3_REGION_NAME=<bucket-region>
AWS_QUERYSTRING_AUTH=false
```

Add `AWS_S3_CUSTOM_DOMAIN=<public-media-or-CDN-hostname>` when the provider gives
you one. With `AWS_QUERYSTRING_AUTH=false`, configure the bucket so uploaded
objects can be read publicly; alternatively set it to `true` for signed URLs.
Never commit these credentials.

The database volume only contains PostgreSQL data and never contains uploaded
images.

### 4. Generate a domain and deploy

Railway normally reads both commands from `railway.json`, so the command fields
in the dashboard may be left empty. Keep the default **Railpack** builder shown
in the dashboard. If Railway does not detect the repository configuration, enter
these commands manually under **Smart-QR > Settings**:

**Custom Build Command**

```bash
python manage.py collectstatic --noinput
```

**Start Command** (in the Deploy section)

```bash
python manage.py migrate --noinput && gunicorn smartqr.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

Do not put the start command in the build-command field. The build command
collects CSS and other static assets into the application image. The start
command runs database migrations against the attached PostgreSQL service and
then starts the web server on the internal port supplied by Railway as `PORT`.

1. Open **Smart-QR > Settings > Networking**, click **Generate Domain**, and copy
   the HTTPS hostname. Railway should detect the port on which Gunicorn starts.
   If a domain already has a manually configured **target port**, it must match
   the `PORT` value shown in the deployment (for example, `8080`). Do not enter
   `80` or `443`; Railway handles public HTTP and HTTPS and forwards that traffic
   to the application's internal port.
2. Put that exact hostname into the three URL/host variables in step 2. Railway
   will redeploy when variables change.
3. Confirm the latest deployment says it loaded `railway.json`. The health check
   is `/health/`.
4. Watch the deployment logs. A successful deployment ends with Gunicorn
   listening at `0.0.0.0:<PORT>` (for example, `0.0.0.0:8080`), and the service
   changes to **Online**.

### Open the site

For the domain shown in the Railway networking screen, open:

```text
https://smart-qr-production.up.railway.app/
```

Use `https://` and do not add an internal port to the public URL. The home URL
redirects to the staff dashboard and then to the administrator login when you
are signed out. You can also open the login directly at:

```text
https://smart-qr-production.up.railway.app/admin/login/
```

To confirm the deployment is alive without logging in, visit:

```text
https://smart-qr-production.up.railway.app/health/
```

It should return `{"status": "ok"}`. If the domain displays an application
error, first confirm the deployment is **Online**, Gunicorn's logged listening
port matches the domain's networking target, and `ALLOWED_HOSTS` is exactly
`smart-qr-production.up.railway.app` (without `https://`).

For a custom domain, add it under **Settings > Networking > Custom Domain**, add
the DNS record Railway displays at the DNS provider, and then replace the
Railway hostname in `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and
`PUBLIC_BASE_URL`. Existing QR codes use `PUBLIC_BASE_URL`, so choose the final
domain before printing them.

### 5. Create the first administrator

Open a shell for the deployed Smart-QR service (Railway's service shell, or
`railway ssh` after linking the CLI to the project) and run:

```bash
python manage.py createsuperuser
```

Then sign in at `https://<your-domain>/admin/`. The optional demo records can be
created with `python manage.py seed_sample`; do not run that command if real
production data is already being entered.

### 6. Verify and operate it

Check all of the following after the first deployment:

* `https://<your-domain>/health/` returns a successful response.
* `/admin/` accepts the new administrator account.
* Create a company and person, upload an image, and open the person's public QR
  URL in a private browser window.
* Redeploy once and verify that the uploaded image still loads from the
  Smart-QR volume (or object bucket, if that alternative was selected).
* Enable PostgreSQL backups in Railway (or export backups on a schedule) and
  back up the Smart-QR volume independently. A database backup does not back up
  uploaded images.

If deployment fails, first check for a missing `DATABASE_URL`, an
`ALLOWED_HOSTS` value that incorrectly includes `https://`, a
`CSRF_TRUSTED_ORIGINS` value that omits `https://`, or missing/incorrect
`MEDIA_ROOT` and `SERVE_MEDIA` values.

V1 defaults are UUID public routes, immutable QR targets, R80 active-card billing, South African locale/timezone, and staff-only management. Back up PostgreSQL and uploaded media independently.
