#!/bin/bash


# run python server
python manage.py runserver --settings=inventory_management_system.settings_local &

#after that run django_q for background jobs
python manage.py qcluster --settings=inventory_management_system.settings_local

