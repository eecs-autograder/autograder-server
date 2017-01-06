FROM python:3.5-onbuild

VOLUME /usr/src/app

RUN python3 -m pip install uwsgi ipython
