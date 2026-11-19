#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

EXPERIMENT="${1:-}"

case "$EXPERIMENT" in
    B11)
        VERSION="11.0.1"
        EXPERIMENT_DIR="$ROOT_DIR/experiments/B11-cardano"
        SHA256="40e88a543564251338c4888ef79fde51d2306c18b48ac308c9eab3220e3a13f0"
        ;;
    *)
        echo "Usage: $0 B11"
        echo "Other experiments will be added after validation."
        exit 1
        ;;
esac

INSTALL_DIR="$ROOT_DIR/resources/cardano/$VERSION"
LINK_PATH="$EXPERIMENT_DIR/resources/cardano-static"

ARCHIVE="cardano-node-${VERSION}-linux-amd64.tar.gz"
URL="https://github.com/IntersectMBO/cardano-node/releases/download/${VERSION}/${ARCHIVE}"

echo "Experiment: $EXPERIMENT"
echo "Cardano Node version: $VERSION"

mkdir -p "$ROOT_DIR/resources/cardano"
mkdir -p "$EXPERIMENT_DIR/resources"

if [[ ! -x "$INSTALL_DIR/bin/cardano-node" ||
      ! -x "$INSTALL_DIR/bin/cardano-cli" ]]; then

    if [[ -e "$INSTALL_DIR" ]]; then
        echo "ERROR: Incomplete installation exists: $INSTALL_DIR"
        echo "Inspect it manually before retrying."
        exit 1
    fi

    echo "Downloading official Cardano release..."

    TEMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TEMP_DIR"' EXIT

    curl -fL --retry 3 \
        -o "$TEMP_DIR/$ARCHIVE" \
        "$URL"

    echo "$SHA256  $TEMP_DIR/$ARCHIVE" | sha256sum -c -

    mkdir -p "$TEMP_DIR/extracted"

    tar -xzf "$TEMP_DIR/$ARCHIVE" \
        -C "$TEMP_DIR/extracted"

    test -x "$TEMP_DIR/extracted/bin/cardano-node"
    test -x "$TEMP_DIR/extracted/bin/cardano-cli"

    mv "$TEMP_DIR/extracted" "$INSTALL_DIR"
fi

RELATIVE_TARGET="../../../resources/cardano/$VERSION"

if [[ -L "$LINK_PATH" ]]; then
    if [[ "$(readlink -f "$LINK_PATH")" != "$INSTALL_DIR" ]]; then
        echo "ERROR: Existing symbolic link points elsewhere."
        exit 1
    fi
elif [[ -e "$LINK_PATH" ]]; then
    echo "ERROR: Existing cardano-static directory detected."
    echo "Inspect it manually before retrying."
    exit 1
else
    ln -s "$RELATIVE_TARGET" "$LINK_PATH"
fi

echo
echo "Verifying Cardano binaries..."

"$LINK_PATH/bin/cardano-node" --version
"$LINK_PATH/bin/cardano-cli" --version

echo
echo "Cardano setup completed successfully."
