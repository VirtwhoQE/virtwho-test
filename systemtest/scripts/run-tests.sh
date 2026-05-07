#!/bin/bash
# run-tests.sh -- Execute the virtwho-test pytest suite and copy artifacts
# to TMT_PLAN_DATA for preservation.
set -euo pipefail

readonly VIRTWHO_TEST_DIR="/opt/virtwho-test"

cd "${VIRTWHO_TEST_DIR}"

echo "=========================================="
echo "Running virt-who regression tests"
echo "=========================================="
echo "Hypervisor: ${HYPERVISOR:-esx}"
echo "Register:   ${REGISTER:-rhsm}"
echo "Compose:    ${RHEL_COMPOSE:-unknown}"
echo "=========================================="

set +e
pytest tests/ \
    --tb=short \
    --junit-xml="${TMT_TEST_DATA}/junit.xml" \
    --html="${TMT_TEST_DATA}/report.html" \
    --self-contained-html \
    -v -s \
    ${PYTEST_ADDOPTS:-}  # intentionally unquoted: allows multiple flags via word splitting
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
