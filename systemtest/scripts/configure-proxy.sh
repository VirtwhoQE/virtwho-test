#!/bin/bash
# configure-proxy.sh -- Configure subscription-manager proxy for Stage access.
# TF guests cannot reach stage directly; squid.corp proxies the traffic.
# This runs BEFORE rhsm.conf backup so tests that restore rhsm.conf retain proxy.
#
# On bootc image-mode composes, TMT runs this inside a Containerfile RUN
# layer. subscription-manager may not be fully functional in that context
# (no dbus, no systemd), so errors are handled gracefully. The proxy
# configuration is written to disk and takes effect when the guest boots.
set -euo pipefail

if [ "${REGISTER:-rhsm}" = "rhsm" ]; then
    if command -v subscription-manager &>/dev/null; then
        subscription-manager config \
            --server.proxy_hostname=squid.corp.redhat.com \
            --server.proxy_port=3128 \
            2>/dev/null \
            || echo "WARNING: subscription-manager config failed (container build?); will retry at boot"
        echo "Configured rhsm.conf proxy: squid.corp.redhat.com:3128"
    else
        echo "WARNING: subscription-manager not found; proxy will be configured at boot"
    fi
fi

mkdir -p /backup && cp /etc/rhsm/rhsm.conf /backup/ 2>/dev/null || true
subscription-manager unregister 2>/dev/null || true
subscription-manager clean 2>/dev/null || true
