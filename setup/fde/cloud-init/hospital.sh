#!/bin/bash
source "$(dirname "$0")/lib.sh"
ubuntu_base
ubuntu_docker
cat >> /etc/environment <<'ENV'
http_proxy="http://10.0.2.100:3128"
https_proxy="http://10.0.2.100:3128"
no_proxy="localhost,127.0.0.1"
ENV
finalize
