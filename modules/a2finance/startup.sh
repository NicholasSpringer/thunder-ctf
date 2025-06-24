#!/bin/bash

# Download and install the Stackdriver Logging Agent
curl -sSO https://dl.google.com/cloudagents/add-logging-agent-repo.sh
sudo bash add-logging-agent-repo.sh
sudo apt-get update
sudo apt-get install -y google-fluentd google-fluentd-catch-all-config

gcloud config set account "${GCLOUD_ACCOUNT}" || true
gcloud config set account "$(gcloud auth list --filter=status:ACTIVE --format='value(account)')" || true

# Ensure the logging agent starts
sudo service google-fluentd start

echo "🪵 Logging agent installed and started."