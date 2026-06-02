#!/bin/bash
# setup-virtwho-test.sh -- Clone virtwho-test repo, install deps, fetch INI,
# and configure dynamic test parameters.
#
# This script runs in the TMT prepare phase. On bootc image-mode composes it
# executes inside a Containerfile RUN layer where /root is restricted (overlay
# restriction). All /root writes and operations that depend on them (SSH key
# generation, ssh-copy-id) are deferred to run-tests.sh (execute phase).
set -euo pipefail

git clone ${VIRTWHO_TEST_REPO:-https://github.com/VirtwhoQE/virtwho-test.git} \
    --branch ${VIRTWHO_TEST_BRANCH:-main} --depth 1 /opt/virtwho-test
cd /opt/virtwho-test

PIP_EXTRA_ARGS=()
if pip install --help 2>&1 | grep -q -- '--root-user-action'; then
    PIP_EXTRA_ARGS+=(--root-user-action=ignore)
fi
pip install "${PIP_EXTRA_ARGS[@]}" -r requirements.txt

INI_URL=${VIRTWHO_INI_URL:-https://gitlab.cee.redhat.com/RHSM-QE/rhsm-jobs/-/raw/main/src/resources/config/virtwho.ini}
echo "Fetching virtwho.ini from: $INI_URL"
curl -sSfL "$INI_URL" -o /opt/virtwho-test/virtwho.ini

HYP=${HYPERVISOR:-esx}

# Remove hypervisor test files that don't match the configured hypervisor
for f in /opt/virtwho-test/tests/hypervisor/test_*.py; do
    htype=$(basename "$f" .py | sed 's/^test_//')
    if [ "$htype" != "$HYP" ] && [ "$htype" != "default" ]; then
        rm -f "$f"
        echo "Removed non-matching test file: $f"
    fi
done

# Resolve compose: if RHEL_COMPOSE is a TF alias (e.g. RHEL-10-Nightly)
# rather than a full compose ID, resolve the actual latest nightly.
RESOLVED_COMPOSE=${RHEL_COMPOSE:-}
if ! echo "$RESOLVED_COMPOSE" | grep -qP '^RHEL-\d+\.\d+\.\d+-\d+'; then
    RELEASE_MAJOR=$(grep -oP 'release \K\d+' /etc/redhat-release 2>/dev/null || echo "10")
    REPO_BASE=${VIRTWHO_REPO:-http://download.devel.redhat.com}
    COMPOSE_ID_URL="${REPO_BASE}/rhel-${RELEASE_MAJOR}/nightly/RHEL-${RELEASE_MAJOR}/latest-RHEL-${RELEASE_MAJOR}/COMPOSE_ID"
    echo "Resolving latest compose from: $COMPOSE_ID_URL"
    RESOLVED_COMPOSE=$(curl -sSfL "$COMPOSE_ID_URL" 2>/dev/null || echo "")
    if [ -z "$RESOLVED_COMPOSE" ]; then
        RELEASE_VER=$(grep -oP 'release \K[\d.]+' /etc/redhat-release 2>/dev/null || echo "10.0")
        RESOLVED_COMPOSE="RHEL-${RELEASE_VER}"
        echo "WARNING: Could not resolve latest compose, falling back to ${RESOLVED_COMPOSE}"
    else
        echo "Resolved latest compose: ${RESOLVED_COMPOSE}"
    fi
fi

VIRTWHO_NEVRA=$(rpm -qa virt-who 2>/dev/null | head -1)
VIRTWHO_NEVRA=${VIRTWHO_NEVRA:-virt-who}

cd /opt/virtwho-test
sed -i "s|^hypervisor=.*|hypervisor=${HYP}|" virtwho.ini
sed -i "s|^register=.*|register=${REGISTER:-rhsm}|" virtwho.ini
sed -i "/^\[job\]/,/^\[/ s|^rhel_compose=.*|rhel_compose=${RESOLVED_COMPOSE}|" virtwho.ini
sed -i "/^\[virtwho\]/,/^\[/ s|^package=.*|package=${VIRTWHO_NEVRA}|" virtwho.ini
sed -i "/^\[virtwho\]/,/^\[/ s|^password=.*|password=redhat|" virtwho.ini

# hostname/IP-dependent and SSH-key operations are deferred to run-tests.sh
# (execute phase) where the guest is fully booted and /root is writable.
echo "virtwho-test cloned and configured (SSH trust deferred to execute phase)"

# Hypervisor-specific prepare (kubevirt only — no /root or network needed)
if [ "$HYP" = "kubevirt" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    bash "${SCRIPT_DIR}/prepare-kubevirt.sh"
fi
