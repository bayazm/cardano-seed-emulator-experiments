# B12 sensor measurement validator offline verification

**Offline passed. Live execution pending.** Verification used a disposable copy of the Aiken project, a cached stdlib, and saved protocol-9 parameters and era history. The Cardano evaluator used synthetic UTXOs and unsigned transaction bodies. No Docker daemon or live node was contacted.

| Item | Verified result |
| --- | --- |
| Toolchain | Aiken `v1.1.24+bacbeb3`, stdlib `v4.0.0`, Plutus V3, Cardano CLI `11.2.3.0` |
| Source and build | Two validators compiled and appeared in the generated blueprint. |
| New script hash | `f7b1435250172148a3c6c2fc5eccf212062d314cd11744018af5fa29` |
| Script address | `addr_test1wrmmzs6j2qtjzj9rcmp0chkv7gfqvtf3fng3w3qp3t6l52g76x36q` |
| Measurement SHA-256 | `b76cef7674424ef76659031a5cf22f1d9b38316c2fe1e71cdbd12c75fc30ac26` |
| Original script hash | `16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83` |
| Positive CLI evaluation | Exit 0, 41,108 memory units, 15,289,580 CPU steps, 3,475 lovelace execution cost at the saved prices |
| Negative CLI evaluations | Exit 1 for wrong ID, changed temperature, changed humidity, equivalent numeric value with different serialization, and malformed redeemer. Each result identified a Plutus failure for the new script hash. |

All ten Aiken tests passed. The seven new tests cover an accepted matching payload and rejection of a wrong ID, altered temperature, altered humidity, altered serialization, missing datum, and malformed redeemer. The three original tests passed. Missing datum was exercised by the unit test.

The offline body carries a synthetic fee and budget placeholders. The reported 3,475 lovelace is script execution cost at the saved prices. A live balanced transaction needs its own fees, collateral, execution units and four-node inclusion evidence.

The combined blueprint, converted script, test/build logs, generated fixtures and successful offline evaluation logs are stored in the operator's ignored research directory under `b12-sensor-hash/`. The repository provides the sources and exact commands to regenerate them. [Demonstration and regeneration commands](B12_sensor_hash_smart_contract_demo.md)
