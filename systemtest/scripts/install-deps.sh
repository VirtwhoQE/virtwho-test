#!/bin/bash
# install-deps.sh -- Install system and Python dependencies for virt-who testing.
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

podman pull images.paas.redhat.com/rhsmqe/rhsm-squid:latest 2>/dev/null || true
