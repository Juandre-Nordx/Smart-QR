web: python manage.py migrate --noinput && gunicorn smartqr.wsgi:application --bind 0.0.0.0:${PORT:-8000}
