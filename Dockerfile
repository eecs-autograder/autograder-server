FROM python:3.4-onbuild

VOLUME /usr/src/app

RUN python3 autograder-sandbox/setup.py install
