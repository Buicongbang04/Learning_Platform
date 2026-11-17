#!/bin/bash
source "$(dirname "$0")/lib.sh"
ubuntu_base
netplan_default_route
k3s_airgap
k3s_tenant
finalize
