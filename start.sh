#!/bin/sh
echo "Running migrations..."
python manage.py migrate
echo "Starting server..."
gunicorn config.wsgi:application --bind 0.0.0.0:10000 --workers 1 --threads 2
