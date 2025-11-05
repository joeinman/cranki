#!/usr/bin/env bash
# Create a distributable .ankiaddon archive for CrAnki.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

mkdir -p "$DIST_DIR"

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    TIMESTAMP="$(date +"%Y.%m.%d-%H%M")"
    VERSION="$TIMESTAMP"
fi

PACKAGE_NAME="CrAnki-${VERSION}.ankiaddon"
PACKAGE_PATH="$DIST_DIR/$PACKAGE_NAME"

pushd "$ROOT_DIR" >/dev/null

zip -r -9 "$PACKAGE_PATH" \
    manifest.json \
    __init__.py \
    src/ \
    config.json \
    README.md \
    LICENSE \
    -x "__pycache__/*" -x "src/__pycache__/*" > /dev/null

popd >/dev/null

echo "Created addon package: $PACKAGE_PATH"
