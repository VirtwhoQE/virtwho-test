#!/bin/bash
# setup-ssh.sh -- Configure sshd for localhost SSH on the TF guest.
#
# This script ONLY modifies /etc/ssh/sshd_config. It does NOT start
# sshd, write to /root, or call systemctl. Those operations are deferred
# to run-tests.sh (execute phase) where systemd and /root writability
# are guaranteed. This separation is required for bootc image-mode
# composes where the prepare phase runs inside a container build
# without systemd and with /root restricted.
set -euo pipefail

sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

# RHEL 10+ uses /etc/ssh/sshd_config.d/ drop-in files that override the main
# config. Create a high-priority drop-in and neutralize conflicting ones.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=sshd-dropin.sh
source "${SCRIPT_DIR}/sshd-dropin.sh"

ssh-keygen -A 2>/dev/null || echo "WARNING: ssh-keygen -A failed -- sshd may need host keys in execute phase"

echo "sshd configured (service start and /root/.ssh setup deferred to execute phase)"
