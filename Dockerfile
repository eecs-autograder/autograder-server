FROM python:3.4-onbuild

RUN pip3 install google-api-python-client

VOLUME /usr/src/app
