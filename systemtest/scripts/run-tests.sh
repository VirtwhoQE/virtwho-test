#!/bin/bash
# run-tests.sh -- Execute the virtwho-test pytest suite and copy artifacts
# to TMT_PLAN_DATA for preservation.
set -euo pipefail

is_bootc() {
  command -v bootc > /dev/null && \
  bootc status --format=humanreadable 2>/dev/null | grep -q 'image'
}

# On bootc guests /opt is immutable at runtime. Copy the test directory
# to a writable location so we can modify virtwho.ini and write artifacts.
if is_bootc && [ -d /opt/virtwho-test ]; then
  WRITABLE_DIR="${TMT_PLAN_DATA:-/var/tmp}/virtwho-test"
  echo "Image-mode: copying /opt/virtwho-test to writable ${WRITABLE_DIR}"
  rm -rf "$WRITABLE_DIR"
  cp -a /opt/virtwho-test "$WRITABLE_DIR"
  VIRTWHO_TEST_DIR="$WRITABLE_DIR"
elif is_bootc; then
  echo "ERROR: bootc detected but /opt/virtwho-test not found (prepare phase may have failed)"
  exit 1
else
  VIRTWHO_TEST_DIR="/opt/virtwho-test"
fi
readonly VIRTWHO_TEST_DIR

# --- Runtime SSH setup (runs in execute phase for both standard and image-mode) ---
# setup-ssh.sh (prepare) only modifies sshd_config. Everything that needs
# systemd or /root writability happens here.
echo "Setting up SSH for localhost testing..."
mkdir -p /root/.ssh && chmod 700 /root/.ssh
printf 'Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile /root/.ssh/known_hosts\n\n' > /root/.ssh/config
chmod 600 /root/.ssh/config

# Ensure password auth is enabled (RHEL 10+ drop-in configs may override sshd_config)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=sshd-dropin.sh
source "${SCRIPT_DIR}/sshd-dropin.sh"

echo "redhat" | passwd --stdin root
ssh-keygen -A 2>/dev/null || true
systemctl restart sshd

GUEST_IP=$(hostname -I | awk '{print $1}')
GUEST_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
if echo "$GUEST_HOSTNAME" | grep -qE 'localhost|unused|openshift'; then
    GUEST_HOSTNAME="virtwho-$(head /dev/urandom | tr -dc a-z0-9 | head -c8).redhat.com"
    hostnamectl set-hostname "$GUEST_HOSTNAME"
fi
grep -q "$GUEST_IP" /etc/hosts || echo "$GUEST_IP $GUEST_HOSTNAME" >> /etc/hosts

# --- Runtime virtwho.ini fixups (deferred from setup-virtwho-test.sh) ---
# Server IP and SSH trust require the guest to be booted with /root writable.
cd "${VIRTWHO_TEST_DIR}"
sed -i "/^\[virtwho\]/,/^\[/ s|^server=.*|server=${GUEST_IP}|" virtwho.ini

HYP=${HYPERVISOR:-esx}
if [ "$HYP" = "libvirt" ]; then
    HYP_SERVER=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^server=/{print \$2}" virtwho.ini | tr -d ' ')
    HYP_USER=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^username=/{print \$2}" virtwho.ini | tr -d ' ')
    HYP_PASS=$(awk -F= "/^\[${HYP}\]/{f=1;next} /^\[/{f=0} f&&/^password=/{print \$2}" virtwho.ini | tr -d ' ')
    if [ -n "$HYP_SERVER" ]; then
        echo "Setting up SSH trust to $HYP hypervisor at $HYP_SERVER"
        ssh-keyscan -p 22 "$HYP_SERVER" >> /root/.ssh/known_hosts 2>&1 || true

        if [ -n "${CCT_SSH_KEY_B64:-}" ]; then
            echo "Using injected SSH key (CCT_SSH_KEY_B64)"
            echo "$CCT_SSH_KEY_B64" | base64 -d > /root/.ssh/id_rsa
            chmod 600 /root/.ssh/id_rsa
            ssh-keygen -y -f /root/.ssh/id_rsa > /root/.ssh/id_rsa.pub
        else
            echo "Generating ephemeral SSH keypair"
            rm -f /root/.ssh/id_rsa /root/.ssh/id_rsa.pub
            ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa -C "virtwho-qe" -q
            if [ -n "$HYP_PASS" ]; then
                sshpass -p "$HYP_PASS" ssh-copy-id -i /root/.ssh/id_rsa.pub \
                    -o StrictHostKeyChecking=no "${HYP_USER:-root}@${HYP_SERVER}" || true
            fi
        fi

        cp /root/.ssh/id_rsa /root/.ssh/virtwho-qe
        cp /root/.ssh/id_rsa.pub /root/.ssh/virtwho-qe.pub

        ssh -o StrictHostKeyChecking=no -o BatchMode=yes \
            "${HYP_USER:-root}@${HYP_SERVER}" hostname \
            && echo "SSH to $HYP_SERVER: OK" \
            || echo "WARNING: SSH to $HYP_SERVER failed (tests may fail)"
    fi
fi

# --- Image-mode-specific adjustments ---
if is_bootc; then
  echo "Image-mode (bootc) detected"

  if command -v podman > /dev/null; then
    podman pull images.paas.redhat.com/rhsmqe/rhsm-squid:latest 2>/dev/null || true
  fi

  # Auto-exclude image-mode-incompatible tests. Extract any existing -m
  # expression from PYTEST_ADDOPTS, combine it with "not notImageMode",
  # and pass the result as a separate quoted -m argument to pytest.
  # NOTE: The -m extraction below only handles a single unquoted token
  # (e.g. "-m gating"). Compound expressions like '-m "tier1 and gating"'
  # are not supported — use IMAGEMODE_PYTEST_MARKER env var to override.
  IMAGEMODE_MARKER="not notImageMode"
  if echo "${PYTEST_ADDOPTS:-}" | grep -qE '\-m[[:space:]]'; then
    EXISTING_MARKER=$(echo "$PYTEST_ADDOPTS" | sed -E 's/.*-m[[:space:]]+([^[:space:]]+).*/\1/')
    IMAGEMODE_MARKER="(${EXISTING_MARKER}) and not notImageMode"
    PYTEST_ADDOPTS=$(echo "${PYTEST_ADDOPTS}" | sed -E 's/[[:space:]]*-m[[:space:]]+[^[:space:]]+//')
  fi
  export PYTEST_ADDOPTS
  export IMAGEMODE_MARKER
  echo "PYTEST_ADDOPTS adjusted for image-mode: ${PYTEST_ADDOPTS:-} -m '${IMAGEMODE_MARKER}'"
fi

cd "${VIRTWHO_TEST_DIR}"

echo "=========================================="
echo "Running virt-who regression tests"
echo "=========================================="
echo "Hypervisor: ${HYPERVISOR:-esx}"
echo "Register:   ${REGISTER:-rhsm}"
echo "Compose:    ${RHEL_COMPOSE:-unknown}"
echo "Image-mode: $(is_bootc && echo yes || echo no)"
echo "=========================================="

MARKER_ARGS=()
if [ -n "${IMAGEMODE_MARKER:-}" ]; then
  MARKER_ARGS=(-m "${IMAGEMODE_MARKER}")
fi

IGNORE_ARGS=()
if is_bootc; then
  # test_hypervisors_state.py imports hypervisor package which writes a log
  # file at import time — fails on the read-only bootc filesystem during
  # collection before markers can deselect it.
  IGNORE_ARGS=(--ignore=tests/others/test_hypervisors_state.py)
fi

set +e
pytest tests/ \
    --tb=short \
    --junit-xml="${TMT_TEST_DATA}/junit.xml" \
    --html="${TMT_TEST_DATA}/report.html" \
    --self-contained-html \
    -v -s \
    ${PYTEST_ADDOPTS:-} \
    "${MARKER_ARGS[@]}" \
    "${IGNORE_ARGS[@]}"
TEST_EXIT_CODE=$?
set -e

echo ""
echo "=========================================="
echo "Test Execution Complete"
echo "Exit Code: ${TEST_EXIT_CODE}"
echo "=========================================="

if [ -n "${TMT_PLAN_DATA:-}" ]; then
    for artifact in junit.xml report.html; do
        if [ -f "${TMT_TEST_DATA}/${artifact}" ]; then
            cp "${TMT_TEST_DATA}/${artifact}" "${TMT_PLAN_DATA}/" || true
            echo "Copied ${artifact} to TMT_PLAN_DATA"
        fi
    done
fi

exit $TEST_EXIT_CODE
