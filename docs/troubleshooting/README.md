# Troubleshooting

| Symptom | Check |
|---|---|
| `ModuleNotFoundError: seedemu` | Activate the environment for the pinned SEED checkout and run the import check in the installation guide. |
| Docker says `compose` is unknown | Check standalone `docker-compose version`. Use the tested 1.27.4 syntax or validate with your Compose plugin. |
| Binary absent or exec format error | Check that the archive extracted `bin/` directly under `resources/cardano-static/` and both tools report Linux x86-64 and the documented versions. |
| Genesis file or producer credential absent | Run the generator in a clean experiment copy. Keep all era files and generated credentials together. |
| Genesis hash or protocol startup error | Confirm configured filenames, update hashes only through appropriate CLI era hash commands and use an empty dedicated DB root for each new genesis. |
| Socket absent or no block production | Check container logs, configured start time, producer credentials and networking. Repeat tip queries after the start time. |
| Transaction builds but confirmation fails | Check the sender UTXO, network magic, fees, validity window, block production and observer nodes. Check the confirmed ledger output with the transaction ID before retrying. |
| B13 TCP connects without catch-up | Check network magic, independent genesis identities and common ledger points. Check that A has a matching producer/relay configuration and the candidate is using the expected chain. |
| B15/B16 registry controller cannot import | Provide the local applied script address and policy ID files in `network/deployment/registry/`. Verify the container names and UTXO/revision before control operations. |
| DID enrollment or authentication fails | Check the trusted public key, local enrollment, DID-to-node mapping, clock, challenge lifetime and the candidate sidecar interface. |
