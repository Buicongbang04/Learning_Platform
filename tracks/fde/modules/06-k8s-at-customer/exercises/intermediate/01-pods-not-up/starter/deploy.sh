#!/bin/sh
set -eu
cd "$HOME"
tar -xf quillo-1.0.0.tar
cd quillo-1.0.0
helm upgrade --install quillo chart/quillo-1.0.0.tgz -n quillo -f "$HOME/deploy/values.yaml"
