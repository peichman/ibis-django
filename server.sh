#!/bin/bash

# wrapper script for running the ibis application in a docker container

# gather the static resources
./manage.py collectstatic

# run the app
exec waitress-serve --listen 0.0.0.0:8000 ibis.wsgi:application
