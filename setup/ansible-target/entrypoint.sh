#!/bin/sh
set -eu
if [ -z "${DEVOPS_EX_AUTHORIZED_KEY:-}" ]; then
  echo "Thiếu DEVOPS_EX_AUTHORIZED_KEY" >&2
  exit 1
fi
ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
install -d -m 0700 /root/.ssh
printf '%s\n' "$DEVOPS_EX_AUTHORIZED_KEY" > /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys
unset DEVOPS_EX_AUTHORIZED_KEY
exec /usr/sbin/sshd -D -e
