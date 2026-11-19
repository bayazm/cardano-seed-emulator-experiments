# File disposition

The existing workspace experiment tree and pre-existing bulk inventory were moved intact into `.local-research/`. Originals were accessed read-only. The list below records each source file selected for the release and any change made during import.

| Publication path | Action |
|---|---|
| `B11-cardano/blockchain.py` | Corrected labels and isolated default runtime root |
| `B11-cardano/config/private-testnet-d0/config.json` | Removed historical era genesis hashes from template |
| `B11-cardano/config/private-testnet-d0/topology-node1.json` | Preserved byte-for-byte |
| `B11-cardano/config/private-testnet-d0/topology-node2.json` | Preserved byte-for-byte |
| `B11-cardano/config/private-testnet-d0/topology-node3.json` | Preserved byte-for-byte |
| `B11-cardano/config/private-testnet-d0/topology-node4.json` | Preserved byte-for-byte |
| `B11-cardano/config/specs/shelley-spec.json` | Derived from active Shelley configuration; cleared deployment bindings and original start time |
| `B12-cardano/blockchain.py` | Corrected labels and isolated default runtime root |
| `B12-cardano/config/private-testnet-conway-v2/config.json` | Removed historical era genesis hashes from template |
| `B12-cardano/config/private-testnet-conway-v2/topology-node1.json` | Preserved byte-for-byte |
| `B12-cardano/config/private-testnet-conway-v2/topology-node2.json` | Preserved byte-for-byte |
| `B12-cardano/config/private-testnet-conway-v2/topology-node3.json` | Preserved byte-for-byte |
| `B12-cardano/config/private-testnet-conway-v2/topology-node4.json` | Preserved byte-for-byte |
| `B12-cardano/config/specs/shelley-spec.json` | Derived from active Shelley configuration; cleared deployment bindings and original start time |
| `B12-cardano/send-metadata.sh` | Preserved byte-for-byte |
| `B12-cardano/cardano_transaction.py` | Preserved byte-for-byte |
| `B12-cardano/benchmark_cardano.py` | Preserved byte-for-byte |
| `B12-cardano/analyze_benchmark.py` | Preserved byte-for-byte |
| `B12-cardano/monitor_blocks.py` | Preserved byte-for-byte |
| `B12-cardano/sensor-prototype/verification/verify_sensor.py` | Preserved byte-for-byte |
| `B12-cardano/smart-contract/sensor-validation/aiken.toml` | Preserved byte-for-byte |
| `B12-cardano/smart-contract/sensor-validation/aiken.lock` | Preserved byte-for-byte |
| `B12-cardano/smart-contract/sensor-validation/validators/sensor_validator.ak` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/blockchain.py` | Corrected labels and isolated default runtime root |
| `B13-cardano-interoperability-v2/config/network-A/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-interoperability-v2/config/network-A/topology-node1.json` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/config/network-A/topology-node2.json` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/config/network-B/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-interoperability-v2/config/network-B/topology-node3.json` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/config/specs/shelley-spec-A.json` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/config/specs/shelley-spec-B.json` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/scripts/update_genesis_hashes.py` | Preserved byte-for-byte |
| `B13-cardano-interoperability-v2/scripts/prepare_final_genesis.sh` | Preserved byte-for-byte |
| `B13-cardano-node-join/blockchain.py` | Corrected labels and isolated default runtime root |
| `B13-cardano-node-join/config/network-A/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-node-join/config/network-A/topology-node1.json` | Preserved byte-for-byte |
| `B13-cardano-node-join/config/network-A/topology-node2.json` | Preserved byte-for-byte |
| `B13-cardano-node-join/config/network-B/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-node-join/config/network-B/topology-node3.json` | Preserved byte-for-byte |
| `B13-cardano-node-join/config/specs/shelley-spec-A.json` | Preserved byte-for-byte |
| `B13-cardano-node-join/config/specs/shelley-spec-B.json` | Preserved byte-for-byte |
| `B13-cardano-node-join/scripts/update_genesis_hashes.py` | Preserved byte-for-byte |
| `B13-cardano-node-join/scripts/prepare_same_time_genesis.sh` | Preserved byte-for-byte |
| `B13-cardano-same-magic/blockchain.py` | Corrected labels and isolated default runtime root |
| `B13-cardano-same-magic/config/network-A/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-same-magic/config/network-A/topology-node1.json` | Preserved byte-for-byte |
| `B13-cardano-same-magic/config/network-A/topology-node2.json` | Preserved byte-for-byte |
| `B13-cardano-same-magic/config/network-B/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-same-magic/config/network-B/topology-node3.json` | Preserved byte-for-byte |
| `B13-cardano-same-magic/config/specs/shelley-spec-A.json` | Preserved byte-for-byte |
| `B13-cardano-same-magic/config/specs/shelley-spec-B.json` | Preserved byte-for-byte |
| `B13-cardano-same-magic/scripts/update_genesis_hashes.py` | Preserved byte-for-byte |
| `B13-cardano-same-magic/scripts/prepare_same_magic_genesis.sh` | Preserved byte-for-byte |
| `B13-cardano-same-time/blockchain.py` | Corrected labels and isolated default runtime root |
| `B13-cardano-same-time/config/network-A/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-same-time/config/network-A/topology-node1.json` | Preserved byte-for-byte |
| `B13-cardano-same-time/config/network-A/topology-node2.json` | Preserved byte-for-byte |
| `B13-cardano-same-time/config/network-B/config.json` | Removed historical era genesis hashes from template |
| `B13-cardano-same-time/config/network-B/topology-node3.json` | Preserved byte-for-byte |
| `B13-cardano-same-time/config/specs/shelley-spec-A.json` | Preserved byte-for-byte |
| `B13-cardano-same-time/config/specs/shelley-spec-B.json` | Preserved byte-for-byte |
| `B13-cardano-same-time/scripts/update_genesis_hashes.py` | Preserved byte-for-byte |
| `B13-cardano-same-time/scripts/prepare_same_time_genesis.sh` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/blockchain.py` | Corrected labels and isolated default runtime root |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/config.json` | Removed historical era genesis hashes from template |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/topology-node1.json` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/topology-node2.json` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/topology-node3.json` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/topology-node4.json` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/config/private-testnet-conway-v2/topology-node5.json` | Preserved byte-for-byte |
| `B14-cardano-relay-admission/config/specs/shelley-spec.json` | Derived from active Shelley configuration; cleared deployment bindings and original start time |
| `B15-cardano-smart-authorization-v2/network/blockchain.py` | Corrected labels and isolated default runtime root |
| `B15-cardano-smart-authorization-v2/network/b15_network.py` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/config.json` | Removed historical era genesis hashes from template |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/topology-node1.json` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/topology-node2.json` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/topology-node3.json` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/topology-node4.json` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/private-testnet-conway-v2/topology-node5.json` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/config/specs/shelley-spec.json` | Derived from active Shelley configuration; cleared deployment bindings and original start time |
| `B15-cardano-smart-authorization-v2/network/scripts/admission_controller.py` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/scripts/enforce_admission.py` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/network/scripts/enforce_revocation.py` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/aiken.toml` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/aiken.lock` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/validators/registry_mint.ak` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/validators/relay_membership.ak` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/lib/b15/authentication.ak` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/lib/b15/authorization.ak` | Preserved byte-for-byte |
| `B15-cardano-smart-authorization-v2/relay-authorization/lib/b15/registry_token.ak` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/blockchain.py` | Corrected labels and isolated default runtime root |
| `B16-cardano-did-authentication/network/b15_network.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/config.json` | Removed historical era genesis hashes from template |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/topology-node1.json` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/topology-node2.json` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/topology-node3.json` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/topology-node4.json` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/private-testnet-conway-v2/topology-node5.json` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/config/specs/shelley-spec.json` | Derived from active Shelley configuration; cleared deployment bindings and original start time |
| `B16-cardano-did-authentication/network/scripts/admission_controller.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/enforce_admission.py` | Excluded inherited B15 helper; preserved locally |
| `B16-cardano-did-authentication/network/scripts/enforce_revocation.py` | Excluded inherited B15 helper; preserved locally |
| `B16-cardano-did-authentication/network/scripts/b16_integrated_admission.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/b16_remote_admission_gateway.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/b16_n15_admission_gateway.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/b16_n15_controlled_gateway.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/b16_n15_firewall_controller.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/b16_n17_revocation_controller.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/__init__.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/create_authority.py` | Isolated administrator credentials under the runtime root |
| `B16-cardano-did-authentication/network/scripts/did_auth/enrollment.py` | Isolated administrator credentials under the runtime root |
| `B16-cardano-did-authentication/network/scripts/did_auth/identity.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/prototype.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/registry_policy.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/test_integrated_identity.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/test_registry_policy.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/sidecar/remote_auth.py` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/network/scripts/did_auth/sidecar/Dockerfile` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/aiken.toml` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/aiken.lock` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/validators/registry_mint.ak` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/validators/relay_membership.ak` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/lib/b15/authentication.ak` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/lib/b15/authorization.ak` | Preserved byte-for-byte |
| `B16-cardano-did-authentication/relay-authorization/lib/b15/registry_token.ak` | Preserved byte-for-byte |

Excluded categories include generated genesis and credentials, archives, release binaries, run-specific deployment values, signed transactions, duplicate prototypes, copied transaction utilities in B14, raw captures and build contexts.

Additional adjustments made after checks:

- B12 shell helper now points at the active Conway credentials and address files. The synthetic metadata examples are new.
- B15 v2 controller container names were matched to the compiler's emitted `b15-` names. B16's inherited B15 enforcement helpers were kept in `.local-research/copied-legacy-helpers/`; B16 retains its own controllers.
- B16 N17 revocation takes the confirmed UTXO as an argument with the existing equality check preserved.
- The common generator uses a placeholder Shelley start in its single-network templates because the CLI requires the input field. The invocation supplies an actual future start.
- `scripts/prepare-genesis.py`, `scripts/validate-static.py`, the audit documents and all experiment READMEs are publication additions.
