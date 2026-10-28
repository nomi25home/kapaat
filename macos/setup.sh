#!/usr/bin/env bash
# setup.sh — one-time: create Python venv next to the repo so Kapaat.app can find it.
# Run once after cloning: cd kapaat && ./macos/setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Creating Python venv at $REPO_DIR/.venv …"
python3 -m venv "$REPO_DIR/.venv"

echo "→ Installing dependencies…"
"$REPO_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet

echo ""
echo "✓ Setup complete."
echo ""
echo "Now build the macOS app:"
echo "  cd macos && ./build.sh"
echo ""
echo "Then open the bundle:"
echo "  open macos/build/Kapaat.app"
