#!/bin/bash
curl -sSO https://dl.google.com/cloudagents/add-logging-agent-repo.sh
sudo bash add-logging-agent-repo.sh
sudo apt-get update
sudo apt-get install google-fluentd
sudo apt-get install -y google-fluentd-catch-all-config
sudo service google-fluentd start
sudo -i
sudo mkdir /home/secretuser
sudo echo "secret" > /home/secretuser/secret.txt
logout