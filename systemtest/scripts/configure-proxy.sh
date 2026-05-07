#!/bin/bash
# configure-proxy.sh -- Configure subscription-manager proxy for Stage access.
# TF guests cannot reach stage directly; squid.corp proxies the traffic.
# This runs BEFORE rhsm.conf backup so tests that restore rhsm.conf retain proxy.
set -euo pipefail

if [ "${REGISTER:-rhsm}" = "rhsm" ]; then
    subscription-manager config \
        --server.proxy_hostname=squid.corp.redhat.com \
        --server.proxy_port=3128
    echo "Configured rhsm.conf proxy: squid.corp.redhat.com:3128"
fi

mkdir -p /backup && cp /etc/rhsm/rhsm.conf /backup/ 2>/dev/null || true
subscription-manager unregister 2>/dev/null || true
subscription-manager clean 2>/dev/null || true
