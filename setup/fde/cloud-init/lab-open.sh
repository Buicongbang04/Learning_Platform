#!/bin/bash
source "$(dirname "$0")/lib.sh"
ubuntu_base
ubuntu_docker
apt-get install -y --no-install-recommends docker-compose-v2
echo "docker-compose-v2 $(dpkg-query -W -f='${Version}' docker-compose-v2)"
finalize
