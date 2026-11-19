# Fresh genesis and credentials

From the repository root after installing the corresponding binaries, run the following for one experiment. Every fresh generation produces new credentials and hashes.

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B12-cardano --minutes 30
```

The generator uses the active Shelley specification with empty deployment maps. It requests fresh delegated stake, funding and producer credentials from Cardano CLI, sets the scenario's initial protocol version and writes four era genesis files and their hashes to the node config. Byron uses the Byron-specific hash command. The topology files are static inputs. Choose a start far enough ahead for a first Docker build and preserve the full generated set with its corresponding runtime directories for a continued run.

For B13 the generator creates A and B independently. Same-magic uses a 20-minute B offset for the fresh comparison. The archived same-magic run used a larger stagger because it retained A from an earlier run. Same-time and node-join generate equal genesis times with distinct genesis identities. For a deliberate continued-ledger variant, copy A's complete matching generated/configuration set into a fresh experiment copy and arrange explicit storage continuity using `CARDANO_EXPERIMENT_RUNTIME`. Verify both A genesis hashes and block points before comparison. Existing databases require their original matching genesis. Use a fresh working copy after a failed partial generation.

The generator does not reconstruct historical B15/B16 wallets, funding or script application. Build the minting policy with a current one-use input and the policy’s fixed `B15_REGISTRY` token name. Apply the membership validator with the freshly generated administrator verification-key hash and new token identity. Compute the script address and lock the singleton registry token with the initial datum. Construct authorization and revocation spends against the actual predecessor UTXO, with current collateral, protocol parameters and a required administrator signature. Treat legacy action redeemers, applied blueprints, addresses and transaction bodies as run-specific. Record each resulting policy ID, script address and confirmed registry UTXO locally. Use the [registry deployment helper and procedure](registry-procedure.md) to apply these parameters and construct transactions against a new live ledger. Fresh live execution remains pending.

## B15/B16 registry data

The membership validator parameters are the administrator verification-key hash, minted policy ID and token name bytes. Apply the one-shot minting policy first because it binds the fresh funding input. Compute its policy ID before applying the spending validator. The mint policy's redeemer is an integer; the historical initialization used zero. Once funding and collateral are prepared, record the seed input, policy ID, spending validator hash, address and confirmed registry UTXO separately.

The registry datum uses constructor 0 with fields in this order:

| Field | Encoding | Fresh instance |
|---|---|---|
| `node_id` | Bytes containing the UTF-8 node label | `AS184` for the published topology |
| `node_ip` | Bytes containing the UTF-8 address | `10.184.0.71` for the published topology |
| `authorized` | Constructor 0 for false or 1 for true, no fields | False initially |
| `revision` | Integer | 0 initially |

The spending redeemer is constructor 0 with two fields. The first is the action constructor, 0 for authorize or 1 for revoke, with no fields. The second is the full proposed registry state. Preserve node ID and IP, change the Boolean as directed and increment the revision by one. The validator requires exactly one continuation at the same script address and checks the input/output registry token. Preserve sufficient ADA for the continuing output, use a separate collateral input, and confirm each transition before exercising the off-chain rule controller.

The templates in `config/` carry protocol settings. Check the generated era files for actual allocations and compare the live UTXO set before spending. Newer CLI output can also represent initialization data under era `extraConfig` sections.
