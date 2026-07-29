#!/bin/bash
# install-deps.sh -- Install system and Python dependencies for virt-who testing.
#
# Runs in the TMT prepare phase. On bootc image-mode composes, TMT
# executes this inside a Containerfile RUN layer (no systemd, no
# network services). All commands must work in that context.
set -euo pipefail

dnf -y install python3-pip git gcc python3-devel openssh-clients \
    libvirt-client python3-libvirt openssh-server expect sshpass podman

# TEST_RPMS is set by the cct-gate pipeline after parsing Brew UMB messages.
# When present, install the specific gated build; otherwise fall back to the
# compose/repo version of virt-who.
if [[ -n "${TEST_RPMS:-}" ]]; then
    echo "Gating mode: installing RPMs from TEST_RPMS"
    # shellcheck disable=SC2086
    dnf -y install --allowerasing ${TEST_RPMS} \
        || { echo "ERROR: failed to install gated RPMs: ${TEST_RPMS}"; exit 2; }
else
    dnf -y install virt-who
fi

# On image-mode container builds, systemd is not running so
# systemctl will fail. The podman pull is deferred to run-tests.sh
# which executes after the guest boots with systemd available.
if systemctl is-system-running &>/dev/null; then
    podman pull images.paas.redhat.com/rhsmqe/rhsm-squid:latest 2>/dev/null || true
else
    echo "No systemd (container build context); deferring podman pull to execute phase"
fi
