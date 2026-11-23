#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

EXPERIMENT="${1:-}"
LOCAL_ARCHIVE="${2:-}"

case "$EXPERIMENT" in
    B11)
        VERSION="11.0.1"
        CLI_VERSION="11.0.0.0"
        EXPERIMENT_DIR="$ROOT_DIR/experiments/B11-cardano"
        SHA256="40e88a543564251338c4888ef79fde51d2306c18b48ac308c9eab3220e3a13f0"
        ;;
    B12|B14|B15)
        VERSION="11.1.3"
        CLI_VERSION="11.2.3.0"
        if [[ "$EXPERIMENT" == B15 ]]; then
            EXPERIMENT_DIR="$ROOT_DIR/experiments/B15-cardano-smart-authorization-v2/network"
        elif [[ "$EXPERIMENT" == B14 ]]; then
            EXPERIMENT_DIR="$ROOT_DIR/experiments/B14-cardano-relay-admission"
        else
            EXPERIMENT_DIR="$ROOT_DIR/experiments/B12-cardano"
        fi
        SHA256="530fb99986fbdccc46f9ee0dd86cabb1393b015feac9173cb731d89fa748365f"
        ;;
    *)
        echo "Usage: $0 {B11|B12|B14|B15} [local-archive]" >&2
        exit 1
        ;;
esac

INSTALL_DIR="$ROOT_DIR/resources/cardano/$VERSION"
LINK_PATH="$EXPERIMENT_DIR/resources/cardano-static"

ARCHIVE="cardano-node-${VERSION}-linux-amd64.tar.gz"
URL="https://github.com/IntersectMBO/cardano-node/releases/download/${VERSION}/${ARCHIVE}"

echo "Experiment: $EXPERIMENT"
echo "Cardano Node version: $VERSION"

RELATIVE_TARGET="../../../resources/cardano/$VERSION"
if [[ "$EXPERIMENT" == B15 ]]; then
    RELATIVE_TARGET="../$RELATIVE_TARGET"
fi

verify_installation() {
    local directory="$1" node_output cli_output
    [[ -x "$directory/bin/cardano-node" && -x "$directory/bin/cardano-cli" ]] || return 1
    node_output="$("$directory/bin/cardano-node" --version)" || return 1
    cli_output="$("$directory/bin/cardano-cli" --version)" || return 1
    [[ "$node_output" == "cardano-node $VERSION "* &&
       "$cli_output" == "cardano-cli $CLI_VERSION "* ]] || return 1
    printf '%s\n%s\n' "$node_output" "$cli_output"
}

if [[ -L "$LINK_PATH" ]]; then
    if [[ "$(readlink "$LINK_PATH")" != "$RELATIVE_TARGET" ]]; then
        echo "ERROR: Existing symbolic link has a different target: $LINK_PATH" >&2
        exit 1
    fi
elif [[ -e "$LINK_PATH" ]]; then
    echo "ERROR: Existing path is in the way: $LINK_PATH" >&2
    exit 1
fi

if [[ -e "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
    if ! verify_installation "$INSTALL_DIR"; then
        echo "ERROR: Existing installation is incomplete or incompatible: $INSTALL_DIR" >&2
        exit 1
    fi
else
    mkdir -p "$ROOT_DIR/resources/cardano"
    TEMP_DIR="$(mktemp -d "$ROOT_DIR/resources/cardano/.install-$VERSION.XXXXXXXX")"
    trap 'rm -rf -- "$TEMP_DIR"' EXIT

    if [[ -n "$LOCAL_ARCHIVE" ]]; then
        cp -- "$LOCAL_ARCHIVE" "$TEMP_DIR/$ARCHIVE"
    else
        echo "Downloading official Cardano release..."
        curl -fL --retry 3 -o "$TEMP_DIR/$ARCHIVE" "$URL"
    fi

    printf '%s  %s\n' "$SHA256" "$TEMP_DIR/$ARCHIVE" | sha256sum -c -
    mkdir "$TEMP_DIR/extracted"
    tar -xzf "$TEMP_DIR/$ARCHIVE" -C "$TEMP_DIR/extracted"

    if ! verify_installation "$TEMP_DIR/extracted"; then
        echo "ERROR: Archive did not provide the expected Cardano binaries." >&2
        exit 1
    fi

    mv -nT -- "$TEMP_DIR/extracted" "$INSTALL_DIR"
    if [[ -e "$TEMP_DIR/extracted" ]]; then
        echo "ERROR: Installation path appeared during setup: $INSTALL_DIR" >&2
        exit 1
    fi
fi

mkdir -p "$EXPERIMENT_DIR/resources"
if [[ ! -L "$LINK_PATH" ]]; then
    ln -sT -- "$RELATIVE_TARGET" "$LINK_PATH"
fi
test "$(readlink -f "$LINK_PATH")" = "$(readlink -f "$INSTALL_DIR")"

echo "Cardano setup completed successfully."
