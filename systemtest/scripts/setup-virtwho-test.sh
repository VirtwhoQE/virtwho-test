#!/bin/bash
# setup-virtwho-test.sh -- Clone virtwho-test repo, install deps, fetch INI,
# and configure dynamic test parameters.
set -euo pipefail

git clone ${VIRTWHO_TEST_REPO:-https://github.com/VirtwhoQE/virtwho-test.git} \
    --branch ${VIRTWHO_TEST_BRANCH:-main} --depth 1 /opt/virtwho-test
cd /opt/virtwho-test
pip install --root-user-action=ignore -r requirements.txt

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
GUEST_IP=$(hostname -I | awk '{print $1}')

cd /opt/virtwho-test
sed -i "s|^hypervisor=.*|hypervisor=${HYP}|" virtwho.ini
sed -i "s|^register=.*|register=${REGISTER:-rhsm}|" virtwho.ini
sed -i "/^\[job\]/,/^\[/ s|^rhel_compose=.*|rhel_compose=${RESOLVED_COMPOSE}|" virtwho.ini
sed -i "/^\[virtwho\]/,/^\[/ s|^package=.*|package=${VIRTWHO_NEVRA}|" virtwho.ini
# Use the guest's actual IP (not localhost) so SSH connections from the test
# framework resolve correctly regardless of hostname configuration.
sed -i "/^\[virtwho\]/,/^\[/ s|^server=.*|server=${GUEST_IP}|" virtwho.ini
sed -i "/^\[virtwho\]/,/^\[/ s|^password=.*|password=redhat|" virtwho.ini

# Set up SSH key trust for remote hypervisors (libvirt, rhevm, etc.)
if [ "$HYP" = "libvirt" ] || [ "$HYP" = "rhevm" ]; then
    HYP_SERVER=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^server=/{print \$2}" virtwho.ini | tr -d ' ')
    HYP_USER=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^username=/{print \$2}" virtwho.ini | tr -d ' ')
    HYP_PASS=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^password=/{print \$2}" virtwho.ini | tr -d ' ')
    if [ -n "$HYP_SERVER" ]; then
        echo "Setting up SSH trust to $HYP hypervisor at $HYP_SERVER"
        mkdir -p ~/.ssh && chmod 700 ~/.ssh

        echo "Scanning host keys from $HYP_SERVER..."
        ssh-keyscan -p 22 "$HYP_SERVER" >> ~/.ssh/known_hosts 2>&1
        echo "known_hosts entries: $(wc -l < ~/.ssh/known_hosts)"

        if [ -n "${CCT_SSH_KEY_B64:-}" ]; then
            echo "Using injected SSH key (CCT_SSH_KEY_B64)"
            echo "$CCT_SSH_KEY_B64" | base64 -d > ~/.ssh/id_rsa
            chmod 600 ~/.ssh/id_rsa
            ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub
        else
            echo "No injected SSH key; generating ephemeral keypair"
            rm -f ~/.ssh/id_rsa ~/.ssh/id_rsa.pub
            ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa -C "virtwho-qe" -q
            if [ -n "$HYP_PASS" ]; then
                sshpass -p "$HYP_PASS" ssh-copy-id -i ~/.ssh/id_rsa.pub \
                    -o StrictHostKeyChecking=no "${HYP_USER:-root}@${HYP_SERVER}"
            fi
        fi

        cp ~/.ssh/id_rsa ~/.ssh/virtwho-qe
        cp ~/.ssh/id_rsa.pub ~/.ssh/virtwho-qe.pub

        echo "Verifying SSH connectivity to $HYP_SERVER..."
        ssh -o StrictHostKeyChecking=no -o BatchMode=yes \
            "${HYP_USER:-root}@${HYP_SERVER}" hostname \
            && echo "SSH to $HYP_SERVER: OK" \
            || echo "WARNING: SSH to $HYP_SERVER failed"
        echo "Final known_hosts entries: $(wc -l < ~/.ssh/known_hosts)"
    fi
fi

# Hypervisor-specific prepare
if [ "$HYP" = "kubevirt" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    bash "${SCRIPT_DIR}/prepare-kubevirt.sh"
fi
