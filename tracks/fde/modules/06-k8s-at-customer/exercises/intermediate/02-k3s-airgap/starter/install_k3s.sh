#!/bin/sh
set -eu
src=$HOME/k3s-airgap
sudo install -m 0755 "$src/k3s" /usr/local/bin/k3s
INSTALL_K3S_SKIP_DOWNLOAD=true sh "$src/install.sh"
