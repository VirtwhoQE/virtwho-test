#!/bin/bash
# test-bootc-lint.sh -- Validate that virt-who installs cleanly into a bootc
# base image and passes bootc container lint (no writes to /run or /tmp,
# no duplicate kernels, all boot deps present, etc.).
set -euo pipefail

RHEL_VERSION="${RHEL_COMPOSE%%.*}"
RHEL_VERSION="${RHEL_VERSION##*-}"

if [ -z "${RHEL_VERSION}" ] || [ "${RHEL_VERSION}" -lt 9 ] 2>/dev/null; then
  echo "SKIP: bootc lint requires RHEL >= 9; RHEL_COMPOSE=${RHEL_COMPOSE:-unset}"
  exit 0
fi

BOOTC_BASE="registry.redhat.io/rhel${RHEL_VERSION}/rhel-bootc:latest"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

cat > "${TMPDIR}/Containerfile" <<EOF
FROM ${BOOTC_BASE}
RUN dnf install -y virt-who && dnf clean all
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
