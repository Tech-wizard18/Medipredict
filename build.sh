#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=disease_app.settings.production

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate

echo "==> Seeding disease models..."
python manage.py seed_models

echo "==> Build complete!"
