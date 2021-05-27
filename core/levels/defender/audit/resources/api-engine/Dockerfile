FROM ubuntu:18.04
COPY requirements.txt ./
RUN set -ex; \
    apt-get update; \
    apt-get install -y python3 python3-pip
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./
CMD exec gunicorn --bind :80 --workers 1 --threads 8 main:app