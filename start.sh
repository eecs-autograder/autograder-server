#! /bin/bash

export DJANGO_SETTINGS_MODULE="autograder.settings.production"
sudo service nginx start
uwsgi --ini ./server_config/uwsgi_autograder.ini
