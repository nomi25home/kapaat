#!/usr/bin/env bash
# build.sh — compile and assemble Kapaat.app
# Run from the macos/ directory: ./build.sh
# Requires: Xcode Command Line Tools (xcode-select --install)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Kapaat"
BUNDLE="$SCRIPT_DIR/build/$APP_NAME.app"

# ── Clean ────────────────────────────────────────────────────────────────────
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"

# ── Compile ──────────────────────────────────────────────────────────────────
echo "→ Compiling Swift sources…"
SOURCES=("$SCRIPT_DIR"/Sources/Kapaat/*.swift)
swiftc "${SOURCES[@]}" \
    -framework AppKit \
    -framework WebKit \
    -framework SwiftUI \
    -framework Security \
    -target "$(xcrun --sdk macosx --show-sdk-platform-path 2>/dev/null | sed 's|Platforms.*||')arm64-apple-macosx13.0" \
    -sdk "$(xcrun --sdk macosx --show-sdk-path)" \
    -parse-as-library \
    -o "$BUNDLE/Contents/MacOS/$APP_NAME"

echo "→ Linking fat binary for Apple Silicon + Intel…"
# Attempt a universal build (arm64 + x86_64); ignore errors if one arch unavailable
ARM_BIN="$BUNDLE/Contents/MacOS/${APP_NAME}_arm64"
X86_BIN="$BUNDLE/Contents/MacOS/${APP_NAME}_x86_64"

swiftc "${SOURCES[@]}" \
    -framework AppKit -framework WebKit -framework SwiftUI -framework Security \
    -target "arm64-apple-macosx13.0" \
    -sdk "$(xcrun --sdk macosx --show-sdk-path)" \
    -parse-as-library \
    -o "$ARM_BIN" 2>/dev/null || true

swiftc "${SOURCES[@]}" \
    -framework AppKit -framework WebKit -framework SwiftUI -framework Security \
    -target "x86_64-apple-macosx13.0" \
    -sdk "$(xcrun --sdk macosx --show-sdk-path)" \
    -parse-as-library \
    -o "$X86_BIN" 2>/dev/null || true

if [ -f "$ARM_BIN" ] && [ -f "$X86_BIN" ]; then
    lipo -create "$ARM_BIN" "$X86_BIN" -output "$BUNDLE/Contents/MacOS/$APP_NAME"
    rm "$ARM_BIN" "$X86_BIN"
    echo "   Universal binary created."
else
    # Single-arch compile already left the binary in place above; clean up partials
    rm -f "$ARM_BIN" "$X86_BIN"
fi

# ── Bundle metadata ──────────────────────────────────────────────────────────
echo "→ Writing Info.plist…"
cp "$SCRIPT_DIR/Info.plist" "$BUNDLE/Contents/Info.plist"

# ── Icon ─────────────────────────────────────────────────────────────────────
if command -v rsvg-convert &>/dev/null && [ -f "$SCRIPT_DIR/../brand/icons/kapaat-icon-32.svg" ]; then
    echo "→ Generating AppIcon.icns…"
    ICON_DIR="$(mktemp -d)"
    for size in 16 32 64 128 256 512 1024; do
        rsvg-convert -w $size -h $size \
            "$SCRIPT_DIR/../brand/icons/kapaat-icon-32.svg" \
            > "$ICON_DIR/icon_${size}x${size}.png" 2>/dev/null || true
    done
    iconutil --convert icns --output "$BUNDLE/Contents/Resources/AppIcon.icns" "$ICON_DIR" 2>/dev/null || true
    rm -rf "$ICON_DIR"
fi

echo ""
echo "✓ Built: $BUNDLE"
echo ""
echo "To run:"
echo "  open \"$BUNDLE\""
echo ""
echo "Or drag Kapaat.app to /Applications."
