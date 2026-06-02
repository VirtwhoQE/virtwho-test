#!/bin/bash
# test-bootc-lint.sh -- Validate that virt-who installs cleanly into a bootc
# base image and passes bootc container lint (no writes to /run or /tmp,
# no duplicate kernels, all boot deps present, etc.).
#
# Gated by RUN_BOOTC_LINT=1 or IMAGE_MODE=1 — skips on standard regression
# runs to avoid the ~15m podman build overhead.
set -euo pipefail

if [ "${RUN_BOOTC_LINT:-}" != "1" ] && [ "${IMAGE_MODE:-}" != "1" ]; then
  echo "SKIP: bootc-lint only runs when RUN_BOOTC_LINT=1 or IMAGE_MODE=1"
  exit 0
fi

RHEL_COMPOSE="${RHEL_COMPOSE:-}"
RHEL_VERSION="${RHEL_COMPOSE%%.*}"
RHEL_VERSION="${RHEL_VERSION##*-}"

if ! [[ "${RHEL_VERSION}" =~ ^[0-9]+$ ]] || [ "${RHEL_VERSION}" -lt 9 ]; then
  echo "SKIP: bootc lint requires numeric RHEL >= 9; RHEL_COMPOSE=${RHEL_COMPOSE:-unset} (parsed: ${RHEL_VERSION})"
  exit 0
fi

BOOTC_BASE="${BOOTC_BASE_IMAGE:-registry.redhat.io/rhel${RHEL_VERSION}/rhel-bootc:latest}"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# When TEST_RPMS is set (gating pipeline), install those instead of repo default.
if [ -n "${TEST_RPMS:-}" ]; then
  INSTALL_CMD="dnf install -y ${TEST_RPMS} && dnf clean all"
else
  INSTALL_CMD="dnf install -y virt-who && dnf clean all"
fi

cat > "${TMPDIR}/Containerfile" <<EOF
FROM ${BOOTC_BASE}
RUN ${INSTALL_CMD}
RUN bootc container lint
EOF

echo "=== Containerfile ==="
cat "${TMPDIR}/Containerfile"
echo "====================="

echo "Building bootc lint image (base: ${BOOTC_BASE})..."
BUILD_LOG="${TMPDIR}/build.log"
if ! podman build --no-cache -t virtwho-bootc-lint -f "${TMPDIR}/Containerfile" "${TMPDIR}" 2>&1 | tee "${BUILD_LOG}"; then
  if grep -qi 'unauthorized\|login\|auth token' "${BUILD_LOG}"; then
    echo "SKIP: Cannot pull ${BOOTC_BASE} — registry authentication not available"
    exit 0
  fi
  exit 1
fi

echo "bootc container lint passed"
