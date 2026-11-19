# Configuration audit

| Category | Publication treatment |
|---|---|
| Node configuration and numbered topologies | Retain the active set per launcher. Remove historical genesis hashes from the templates. |
| Shelley generation specification | Retain reusable protocol settings with empty genesis delegation, stake and funding maps. Replace start time during generation. |
| Byron, Shelley, Alonzo and Conway runtime genesis | Generate for each chain as a coherent set with its own credentials. Historical copies are private provenance. |
| KES, VRF, payment, administrator and DID signing material | Generate locally for the new deployment. Operational certificates and verification keys correspond to the generated private material. |
| Aiken source and dependency locks | Publish and rebuild with the recorded toolchain. Applied blueprints and script addresses depend on deployment parameters. |
| Transaction templates and state | Preserve code and reusable metadata formats. Rebuild all addresses, funding/collateral/seed/current registry UTXOs, transaction hashes, signatures and applied policy identifiers. |
| DID documents, enrollment and challenge records | Generate new identities and enrollment records. Keep private keys, transport records and test transcripts local. |
| Historical JSON under archives, generated directories and Docker output | Preserve with existing local copies and exclude from release. |

Historical B11 used slot length 1 s, active slot coefficient 0.05, security parameter 2160 and epoch length 432000. B12/B14/B15/B16 source runtime Shelley files use 86400 slots per epoch with the same slot length and coefficient. The historical B15 v2 and B16 Shelley protocol version is 9.0.
