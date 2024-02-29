#!/bin/bash

# Apply database migrations
python manage.py migrate

# Collect static files (if needed)
# python manage.py collectstatic --noinput

# Start Django development server
python manage.py runserver 0.0.0.0:8000