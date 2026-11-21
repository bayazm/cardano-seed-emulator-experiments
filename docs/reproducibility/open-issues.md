# Open reproducibility issues

| Category | Status and next evidence |
|---|---|
| Documentation | B15/B16 procedures cover the registry and sidecar helpers, their prerequisites, supported entry points and ordering. All nine experiments have a runtime verification plan. Historical evidence stays private, which limits independent reconstruction of those observations. |
| External dependencies | Independent installation of the pinned SEED revision, Python dependencies, Aiken package resolution without the local cache and Docker base-image availability remain unverified. Cardano release binaries must be installed separately. |
| Configuration and deployment | The B15/B16 registry workflow and B16 namespace deployment are implemented. Select live funding and collateral from the fresh ledger. Verify default wallet funding and protocol min-output/collateral rules on the running chain. Verify B16 namespace permissions, Docker access and public/private role staging in the target VM. Continued B13 ledger runs require A's matching history and credentials. |
| Static validation | Registry schemas, Aiken parameter application and role staging passed offline validation. The intended publication checkout is reviewed against its Git index. Repeat against the actual release index after any changes. Historical evidence provenance and an independent clean dependency resolution remain beyond the static checks. |
| Runtime validation | B11 passed its controlled runtime smoke test. Fresh repetition of B12–B16 is outside the publication scope. The release distinguishes historical outcomes, offline checks and the pending runtime evidence for the new B15/B16 helpers. |
| Publication rights | Confirm file-level license scope and applicable collaborator terms before making a release public. |

See the [runtime verification plans](runtime-verification.md), [registry procedure](registry-procedure.md) and [final publication review](../audit/final-publication-review.md).
