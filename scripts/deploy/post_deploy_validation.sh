#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Synapse Trading Platform – Post-Deploy Validation Script
# ---------------------------------------------------------------------------
# Runs the Selenium test-suite against a live deployment (HTTPS domain or IP).
# Usage:
#   ./post_deploy_validation.sh [BASE_URL] [pytest extra args]
# Example:
#   ./post_deploy_validation.sh https://synaptictrading.com -k test_dashboard_loads_completely
# If BASE_URL is omitted, it falls back to the env var $BASE_URL or defaults to
# https://synaptictrading.com.
# ---------------------------------------------------------------------------
set -euo pipefail

# Resolve project root (two directories up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

DOMAIN="${1:-${BASE_URL:-"https://synaptictrading.com"}}"
shift || true

PYTEST_ARGS=${PYTEST_ARGS:-"-m selenium --headless --browser chromium -q"}

echo "📋 Running Selenium validation against ${DOMAIN}"

# Export BASE_URL for conftest fixtures
export BASE_URL="$DOMAIN"

pytest tests/selenium/test_suites $PYTEST_ARGS "$@"

echo "✅ Selenium validation completed" 