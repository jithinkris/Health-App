#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
exec gunicorn core.wsgi --bind "0.0.0.0:${PORT:-8000}"
