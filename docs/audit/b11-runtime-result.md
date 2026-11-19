# B11 controlled runtime result

B11 passed the runtime smoke test on a fresh private network with Cardano Node 11.0.1 and CLI 11.0.0.0. It reused the 22 compatible historical Docker networks while the historical containers were stopped. The operator ran the build and startup commands from the [network reuse report](b11-network-reuse.md) and the run-specific collector. The earlier [preflight](b11-runtime-preflight.md) records the isolated genesis and compilation steps.

| Check | Observation |
|---|---|
| Compose startup | 36 workload containers showed Up. Both image-helper containers exited 0. |
| Block production | AS151 logged `ForgedBlock`. Across five samples, three producers and one relay advanced from block 1 at slot 306 to block 3 at slot 381. |
| Relay synchronization | All four nodes reported the same tip hash within every sample and reported 100.00% sync progress. The final sample was Alonzo epoch 0. AS153 logged additions to its current chain. |
| Chain agreement | The final hash agreed across all four nodes at `9788451448a990445841e8e6a9ecfbaac2801e1ca039cf102ccb77903d59dbd3`. This checks observed chain points. A ledger-state dump and transaction test were outside the collected evidence. |
| TCP/3001 | The relay reached AS150 at `10.150.0.71:3001`. Its net0 capture held 97 packets with zero kernel drops. The collector's 25-second timeout ended the capture with code 124. |

Raw evidence remains outside the source tree at `/tmp/b11-runtime.ZdMSRhh0/evidence/runtime-20261119T011356Z.8kPkZW`. The 8,754-byte PCAP is at `/tmp/b11-runtime.ZdMSRhh0/state/captures/b11-20261119T011356Z.pcap`. This short smoke test establishes startup, production, relay synchronization and TCP reachability for this deployment.

To release the shared network addresses before restarting a historical project, use the targeted stop from the Ubuntu terminal. This preserves evidence, credentials, volumes and networks.

```bash
cd /tmp/b11-runtime.ZdMSRhh0/B11-cardano/output
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml stop
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml ps
```
