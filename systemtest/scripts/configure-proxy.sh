#!/bin/bash
# configure-proxy.sh -- Configure subscription-manager proxy for Stage access.
# TF guests cannot reach stage directly; a proxy is needed to reach Stage.
# This runs BEFORE rhsm.conf backup so tests that restore rhsm.conf retain proxy.
#
# Proxy settings are derived from the HTTPS_PROXY / HTTP_PROXY environment
# variables (set in regression.fmf or by TF). Falls back to a sensible
# default if unset.
#
# On bootc image-mode composes, TMT runs this inside a Containerfile RUN
# layer. subscription-manager may not be fully functional in that context
# (no dbus, no systemd), so errors are handled gracefully. The proxy
# configuration is written to disk and takes effect when the guest boots.
set -euo pipefail

# Parse host and port from the environment proxy URL (set by the TMT plan
# environment block in regression.fmf).  Accepts formats: http://host:port,
# host:port, host.  Falls back to squid.corp.redhat.com:3128 for manual /
# non-TMT invocations so the script remains usable standalone.
_proxy_url="${HTTPS_PROXY:-${HTTP_PROXY:-}}"
if [ -z "$_proxy_url" ]; then
    echo "INFO: HTTPS_PROXY/HTTP_PROXY not set; using default squid.corp.redhat.com:3128"
    _proxy_url="http://squid.corp.redhat.com:3128"
fi
# Strip protocol prefix and trailing slash
_hostport="${_proxy_url#http://}"
_hostport="${_hostport#https://}"
_hostport="${_hostport%/}"
PROXY_HOST="${_hostport%%:*}"
PROXY_PORT="${_hostport##*:}"
# If no port was in the string, default to 3128
[ "$PROXY_PORT" = "$PROXY_HOST" ] && PROXY_PORT=3128

if [ "${REGISTER:-rhsm}" = "rhsm" ] && [ -n "${PROXY_HOST:-}" ]; then
    if command -v subscription-manager &>/dev/null; then
        subscription-manager config \
            --server.proxy_hostname="$PROXY_HOST" \
            --server.proxy_port="$PROXY_PORT" \
            2>/dev/null \
            || echo "WARNING: subscription-manager config failed (container build?); will retry at boot"
        echo "Configured rhsm.conf proxy: ${PROXY_HOST}:${PROXY_PORT}"
    else
        echo "WARNING: subscription-manager not found; proxy will be configured at boot"
    fi
fi

mkdir -p /backup && cp /etc/rhsm/rhsm.conf /backup/ 2>/dev/null || true
subscription-manager unregister 2>/dev/null || true
subscription-manager clean 2>/dev/null || true
