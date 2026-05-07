#!/bin/bash
# prepare-kubevirt.sh -- KubeVirt-specific preparation for virt-who testing.
# Handles SA token injection, kubeconfig generation, and guest VM proxy setup.
#
# NOTE: virt-who's kubevirt backend currently requires cluster-scoped API
# access (list nodes, list VMIs cluster-wide) which is not available in
# namespace-restricted environments like ITUP.Scale.  See CCT-2379.
# Until that bug is fixed upstream, most tests that start the virt-who
# daemon will fail with ApiException(403).
set -euo pipefail

cd /opt/virtwho-test

ini_get() {
    awk -F= "/^\[kubevirt\]/{f=1;next} /^\[/{f=0} f&&/^${1}=/{print \$2}" virtwho.ini | tr -d ' '
}

# Inject the real SA token (passed via KUBEVIRT_TOKEN env var from Jenkins).
# Uses python to avoid sed delimiter collisions if the token contains |, /, &.
if [ -n "${KUBEVIRT_TOKEN:-}" ]; then
    python3 -c "
import re, sys
token = sys.argv[1]
with open('virtwho.ini') as f:
    txt = f.read()
txt = re.sub(
    r'(?m)(^\[kubevirt\].*?^token=).*',
    lambda m: m.group(1) + token,
    txt,
    count=1,
    flags=re.DOTALL,
)
with open('virtwho.ini', 'w') as f:
    f.write(txt)
" "$KUBEVIRT_TOKEN"
    echo "Injected KUBEVIRT_TOKEN into virtwho.ini"
fi

KV_ENDPOINT=$(ini_get endpoint)
KV_TOKEN=$(ini_get token)
KV_CONFIG_FILE=$(ini_get config_file)
KV_CONFIG_NO_CERT=$(ini_get config_file_no_cert)

# Generate kubeconfig YAML from SA token
if [ -n "$KV_ENDPOINT" ] && [ -n "$KV_TOKEN" ] && [ -n "$KV_CONFIG_FILE" ]; then
    echo "Generating kubeconfig at $KV_CONFIG_FILE for $KV_ENDPOINT"
    python3 -c "
import yaml, sys
kc = {
    'apiVersion': 'v1', 'kind': 'Config',
    'clusters': [{'cluster': {'server': sys.argv[1], 'insecure-skip-tls-verify': True}, 'name': 'kubevirt'}],
    'contexts': [{'context': {'cluster': 'kubevirt', 'user': 'ci-runner'}, 'name': 'kubevirt'}],
    'current-context': 'kubevirt',
    'users': [{'name': 'ci-runner', 'user': {'token': sys.argv[2]}}],
}
with open(sys.argv[3], 'w') as f:
    yaml.safe_dump(kc, f, default_flow_style=False)
" "$KV_ENDPOINT" "$KV_TOKEN" "$KV_CONFIG_FILE"
    echo "Kubeconfig written ($(wc -c < "$KV_CONFIG_FILE") bytes)"

    if [ -n "$KV_CONFIG_NO_CERT" ]; then
        cp "$KV_CONFIG_FILE" "$KV_CONFIG_NO_CERT"
        echo "No-cert kubeconfig written to $KV_CONFIG_NO_CERT"
    fi
fi

# Configure proxy on the KubeVirt guest VM so subscription-manager
# can reach stage.  The guest is inside ITUP and has no direct route
# to subscription.rhsm.stage.redhat.com.
KV_GUEST_IP=$(ini_get guest_ip)
KV_GUEST_PORT=$(ini_get guest_port)
KV_GUEST_USER=$(ini_get guest_username)
KV_GUEST_PASS=$(ini_get guest_password)
if [ -n "$KV_GUEST_IP" ] && [ -n "$KV_GUEST_PORT" ]; then
    echo "Configuring proxy on KubeVirt guest VM at ${KV_GUEST_IP}:${KV_GUEST_PORT}"
    sshpass -p "${KV_GUEST_PASS:-redhat}" \
        ssh -o StrictHostKeyChecking=no -p "$KV_GUEST_PORT" \
        "${KV_GUEST_USER:-root}@${KV_GUEST_IP}" \
        "subscription-manager config --server.proxy_hostname=squid.corp.redhat.com --server.proxy_port=3128" \
        && echo "Guest VM proxy configured" \
        || echo "WARNING: Failed to configure guest VM proxy"
fi
