#! /bin/bash

export DJANGO_SETTINGS_MODULE="autograder.settings.production"
sudo service nginx start
sudo service uwsgi start
