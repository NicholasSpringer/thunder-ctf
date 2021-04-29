FROM ubuntu:18.04
COPY requirements.txt ./
ENV VIRTUAL_ENV=/opt/venv
RUN set -ex; \
    apt-get update; \
    apt-get install -y python3 python3-venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install -r requirements.txt; \
    pip install gunicorn
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./
CMD exec gunicorn --bind :80 --workers 1 --threads 8 main:app