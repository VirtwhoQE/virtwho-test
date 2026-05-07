#!/bin/bash
# setup-ssh.sh -- Enable password-based SSH to localhost on the TF guest.
# The TF guest IS the virt-who host; tests SSH to localhost to control virt-who.
set -euo pipefail

echo "redhat" | passwd --stdin root
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl restart sshd

GUEST_IP=$(hostname -I | awk '{print $1}')
GUEST_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
if echo "$GUEST_HOSTNAME" | grep -qE 'localhost|unused|openshift'; then
    GUEST_HOSTNAME="virtwho-$(head /dev/urandom | tr -dc a-z0-9 | head -c8).redhat.com"
    hostnamectl set-hostname "$GUEST_HOSTNAME"
fi
grep -q "$GUEST_IP" /etc/hosts || echo "$GUEST_IP $GUEST_HOSTNAME" >> /etc/hosts

mkdir -p ~/.ssh && chmod 700 ~/.ssh
printf 'Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile ~/.ssh/known_hosts\n\n' > ~/.ssh/config
chmod 600 ~/.ssh/config
