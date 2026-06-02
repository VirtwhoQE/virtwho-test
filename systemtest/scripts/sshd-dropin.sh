#!/bin/bash
# sshd-dropin.sh -- Ensure PasswordAuthentication and PermitRootLogin are
# enabled via a high-priority sshd_config.d drop-in and neutralize any
# conflicting drop-ins. Sourced by setup-ssh.sh (prepare) and run-tests.sh
# (execute) to keep the logic in one place.

mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-virtwho-test.conf <<SSHEOF
PasswordAuthentication yes
PermitRootLogin yes
SSHEOF

for f in /etc/ssh/sshd_config.d/*.conf; do
  [ -f "$f" ] && [ "$f" != "/etc/ssh/sshd_config.d/99-virtwho-test.conf" ] && {
    sed -i 's/^PasswordAuthentication no/# &  # overridden by 99-virtwho-test.conf/' "$f" 2>/dev/null
    sed -i 's/^PermitRootLogin \(no\|prohibit-password\|without-password\)/# &  # overridden by 99-virtwho-test.conf/' "$f" 2>/dev/null
  } || true
done
