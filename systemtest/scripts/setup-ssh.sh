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
# config. Create a high-priority drop-in to ensure our settings take effect.
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-virtwho-test.conf <<SSHEOF
PasswordAuthentication yes
PermitRootLogin yes
SSHEOF

# Neutralize any existing drop-ins that conflict with our settings.
# OpenSSH uses first-match semantics within Include'd files, so earlier
# drop-ins (e.g. 50-redhat.conf) can override our 99-* file.
for f in /etc/ssh/sshd_config.d/*.conf; do
  [ -f "$f" ] && [ "$f" != "/etc/ssh/sshd_config.d/99-virtwho-test.conf" ] && {
    sed -i 's/^PasswordAuthentication no/# &  # overridden by 99-virtwho-test.conf/' "$f" 2>/dev/null
    sed -i 's/^PermitRootLogin \(no\|prohibit-password\|without-password\)/# &  # overridden by 99-virtwho-test.conf/' "$f" 2>/dev/null
  } || true
done

ssh-keygen -A 2>/dev/null || echo "WARNING: ssh-keygen -A failed -- sshd may need host keys in execute phase"

echo "sshd configured (service start and /root/.ssh setup deferred to execute phase)"
