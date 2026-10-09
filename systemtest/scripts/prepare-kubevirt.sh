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
# Uses configparser to safely write the token value without corrupting subsequent lines.
if [ -n "${KUBEVIRT_TOKEN:-}" ]; then
    python3 -c "
import configparser, json, re, ssl, sys, urllib3
token = sys.argv[1]
cfg = configparser.ConfigParser(interpolation=None)
cfg.optionxform = str
cfg.read('virtwho.ini')
if 'kubevirt' in cfg:
    cfg['kubevirt']['token'] = token
    endpoint = cfg['kubevirt'].get('endpoint')
    namespace = cfg['kubevirt'].get('namespace')
    guest_name = cfg['kubevirt'].get('guest_name', 'rhel10-virtwho-guest')

    if endpoint and token and namespace:
        http = urllib3.PoolManager(cert_reqs=ssl.CERT_NONE)
        headers = {'Authorization': f'Bearer {token}'}

        # Discover guest VM node IP
        try:
            r = http.request(
                'GET',
                f'{endpoint}/apis/kubevirt.io/v1/namespaces/{namespace}/virtualmachineinstances/{guest_name}',
                headers=headers,
                timeout=10,
            )
            if 200 <= r.status < 300:
                vmi = json.loads(r.data.decode('utf-8'))
                node_name = vmi.get('status', {}).get('nodeName', '')
                m = re.match(r'^ip-(\d+)-(\d+)-(\d+)-(\d+)\.', node_name)
                if m:
                    discovered_ip = '.'.join(m.groups())
                    cfg['kubevirt']['guest_ip'] = discovered_ip
                    print(f'Discovered guest_ip: {discovered_ip} (node: {node_name})')
        except Exception as e:
            print(f'Warning: guest_ip discovery failed: {e}')

        # Discover guest SSH NodePort service
        try:
            r = http.request(
                'GET',
                f'{endpoint}/api/v1/namespaces/{namespace}/services/virtwho-guest-ssh',
                headers=headers,
                timeout=10,
            )
            if 200 <= r.status < 300:
                svc = json.loads(r.data.decode('utf-8'))
                node_port = svc.get('spec', {}).get('ports', [{}])[0].get('nodePort')
                if node_port:
                    cfg['kubevirt']['guest_port'] = str(node_port)
                    print(f'Discovered guest_port: {node_port}')
        except Exception as e:
            print(f'Warning: guest_port discovery failed: {e}')

with open('virtwho.ini', 'w') as f:
    cfg.write(f, space_around_delimiters=False)
" "$KUBEVIRT_TOKEN"
    echo "Injected KUBEVIRT_TOKEN and updated dynamic coordinates in virtwho.ini"
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
