#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

CLI="$PROJECT_DIR/resources/cardano-static/bin/cardano-cli"

# Shared genesis start time: 20 minutes in the future.
START_TIME="2026-10-29T10:05:16Z"

echo "======================================="
echo "B13 EXPERIMENT 4C - SAME MAGIC AND TIME"
echo "Start time: $START_TIME"
echo "======================================="

# Generate both independent networks.
for NETWORK in B; do

    if [ "$NETWORK" = "A" ]; then
        MAGIC=5555
    else
        MAGIC=5555
    fi

    echo
    echo "Generating Network $NETWORK (magic $MAGIC)"

    GEN_DIR="$PROJECT_DIR/config/generated/network-$NETWORK"
    RUNTIME_DIR="$PROJECT_DIR/config/network-$NETWORK"

    # Refuse to overwrite existing genesis material.
    if [ -e "$GEN_DIR" ]; then
        echo "ERROR: $GEN_DIR already exists."
        echo "Archive it before regenerating."
        exit 1
    fi

    "$CLI" conway genesis create-testnet-data \
        --spec-shelley "$PROJECT_DIR/config/specs/shelley-spec-$NETWORK.json" \
        --genesis-keys 1 \
        --pools 1 \
        --stake-delegators 1 \
        --utxo-keys 1 \
        --total-supply 450000000000 \
        --delegated-supply 300000000000 \
        --testnet-magic "$MAGIC" \
        --start-time "$START_TIME" \
        --out-dir "$GEN_DIR"

    for ERA in byron shelley alonzo conway; do
        cp \
          "$GEN_DIR/$ERA-genesis.json" \
          "$RUNTIME_DIR/$ERA-genesis.json"
    done

done

# Update genesis hashes in both Cardano configurations.
python3 scripts/update_genesis_hashes.py

echo
echo "Final genesis generation completed."
echo "Shared start time: $START_TIME"
