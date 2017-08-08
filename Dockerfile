FROM python:3.5

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app
VOLUME /usr/src/app
