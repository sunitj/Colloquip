#!/usr/bin/env bash
# reset-demo.sh — Clean all prior state before recording a demo
#
# Usage:
#   ./scripts/reset-demo.sh
#
# This removes:
#   - SQLite database files (colloquip.db*)
#   - Alembic version stamps (so migrations re-run on next startup)
#   - Python caches
#   - Frontend build artifacts
#   - Demo test results / videos from prior runs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Colloquium Demo Reset ==="
echo ""

# 1. Remove SQLite databases
echo "[1/5] Removing SQLite databases..."
find "$ROOT_DIR" -maxdepth 2 -name "colloquip.db*" -delete 2>/dev/null && echo "  Removed colloquip.db*" || echo "  No databases found"

# 2. Clear Python caches
echo "[2/5] Clearing Python caches..."
find "$ROOT_DIR/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$ROOT_DIR/tests" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf "$ROOT_DIR/.pytest_cache" 2>/dev/null || true
echo "  Done"

# 3. Clear frontend build artifacts
echo "[3/5] Clearing frontend build artifacts..."
rm -rf "$ROOT_DIR/web/dist" 2>/dev/null && echo "  Removed web/dist" || echo "  No build artifacts"

# 4. Clear demo test results / videos from prior runs
echo "[4/5] Clearing prior demo recordings..."
rm -rf "$ROOT_DIR/demo/test-results" 2>/dev/null && echo "  Removed demo/test-results" || echo "  No prior recordings"

# 5. Clear any lingering Playwright state
echo "[5/5] Clearing Playwright state..."
rm -rf "$ROOT_DIR/.playwright-mcp" 2>/dev/null || true
echo "  Done"

echo ""
echo "=== Reset complete. Ready for a fresh demo! ==="
echo ""
echo "Next steps:"
echo "  1. Start the backend:  uv run uvicorn colloquip.api:create_app --factory --reload"
echo "  2. Start the frontend: cd web && npm run dev"
echo "  3. Run the demo:       cd demo && npx playwright test"
