# Source audit

| Location | Inconsistency | Impact | Treatment |
|---|---|---|---|
| B12, B13, B14, B15 and B16 `blockchain.py` | Inherited B11 descriptions, version lines, AS lists and several startup banners. | Wrong experiment or version shown in operator guidance. | Correct labels against node mappings, local binary version output and Shelley magic. |
| B13 same-magic, same-time and node-join compiler | Repeated distinct-magic banner for matching magic; same-time and node-join reuse part of the same-magic DB tree. | Can lead to accidentally mounting historical state. | Preserve database namespaces, isolate the default root and document intentional reuse. |
| B12 and B14 transaction helpers | Historical experiment layout and Docker service conventions. | Container ambiguity when multiple projects share a daemon. | Document explicit container selection and prepared wallet state. |
| B15/B16 `prepare_v2_genesis.py` | Inherited staging scripts assume prior generated material and use another experiment's DB guard. | A guard can examine the wrong ledger. | Exclude redundant helpers from the release workflow. |
| B15/B16 registry controllers | Historical addresses, policy IDs and candidate assumptions. | Fresh chains require deployment-specific parameters and a verified controller binding. | Retain prototype controller source and document required substitutions. |
| B16 `blockchain.py` and `b15_network.py` | B15 naming survives in the companion module and the launcher banner. | AS185 is a separate host and has no Cardano topology. | Correct the visible banner and comments. Preserve companion module name. |
| B11/B12/B14 and B15/B16 compiler postprocessing | Compose and Dockerfile edits depend on emitted text conventions. | SEED changes that preserve the Python API can still alter the output layout. | Pin the observed SEED commit and report actual check depth. |
| B13 shell scripts | Multiple copied preparation variants select different magic and timing. | Running an inherited script can change the independent variable. | Keep only the applicable recovered generation helpers and document variant-specific runtime state. |

The experiment READMEs describe the active launch/configuration pair and the controls needed to interpret each run.

Post-compilation verification found that B15 v2 emitted `b15-` container names while three control scripts used `b15v2-`. The controller references now match emitted Compose names. B12's retained CIP-20 shell helper was adjusted from the inactive B11 key and address directories to the B12 Conway layout. B16 revocation now requires an explicit current UTXO reference. Those controller and transaction edits were checked statically; no Docker operations were executed.

Per-experiment network roles, active files, observed versions and verification procedures are indexed from the [root README](../../README.md). The [configuration audit](configuration-audit.md) and [dependency map](dependency-map.md) document the inherited and generated inputs. These reports describe the source as observed and label each remaining runtime assumption.
