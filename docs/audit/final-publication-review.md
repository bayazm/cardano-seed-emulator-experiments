# Final publication review

## Repository completeness

Each package has a compiler entry point, active node configuration, numbered topologies, a Shelley generation specification, dependency and genesis instructions, start commands, verification and expected observations, troubleshooting and security limitations. The [dependency map](dependency-map.md) enumerates inputs generated locally. The nine [runtime plans](../reproducibility/runtime-verification.md) specify evidence and cleanup.

| Package | Verified publication material | Pending outside the source package |
|---|---|---|
| B11 | Launcher, four-node profile, producer/relay instructions | Release binaries, generated genesis and credentials, live synchronization |
| B12 | Launcher, four-node profile, transfer and monitoring tools, CIP-20 and sensor fixtures, Aiken project | Locally generated addresses, fresh funding and confirmed transactions |
| B13 interoperability v2 | Two network profiles, distinct-magic specification, paired test instructions | Fresh genesis and protocol/ledger evidence |
| B13 same magic | Two matching-magic profiles and controlled stagger procedure | Fresh independent chains and comparison evidence |
| B13 same time | Two matching-magic profiles and equal-start procedure | Fresh independent chains and comparison evidence |
| B13 node join | Two profiles, staged AS171 startup and same-chain verification | Staged startup and relay convergence |
| B14 | Five-node profile, default-deny rules, staged admission with restoration | New three-phase network evidence |
| B15 v2 | Five-node profile, Aiken source/lock, admission and revocation controllers | Fresh funded, collateralized and applied registry with confirmed transitions |
| B16 | Five Cardano nodes and separate AS185 host, Aiken, enrollment, local identity tests, gateway and candidate sources | Same fresh registry plus sidecar/network namespace setup and full live validation |

Historical B13 helpers are identified as provenance. The shared generator is the documented fresh-run entry point. B12 benchmark metadata and address inputs are produced by its README steps. B15/B16 deployment files are explicit operator inputs, generated networks are local build products, and archived citations are evidence references rather than runtime dependencies.

## Documentation and remaining reproducibility issues

The [classified issue list](../reproducibility/open-issues.md) distinguishes documentation, dependency, configuration, static and runtime gaps. The [B15/B16 registry procedure](../reproducibility/registry-procedure.md) documents funding, collateral, policy application, mint/lock, authorization, authentication where applicable, admission, revocation and evidence. The subsequent [deployment implementation report](b15-b16-deployment.md) describes the new registry and sidecar helpers and supersedes the implementation gaps from this review. Runtime and licensing gates remain.

## Security review

The reviewed source set was inspected for Cardano and DID private material, administrator credentials, hardcoded secrets, user-specific paths, binary archives, databases, captures, build output and backups. The staged rehearsal uses the explicit publication paths listed in the checklist. Generated files and the private local research archive are excluded. The rehearsal staged 161 UTF-8 text files, with zero ignored paths in the index. No private material was identified in that candidate. This is a source review with pattern and path checks, with limited detection for unknown encodings. Generated producer keys remain sensitive inside Docker build contexts and images. B16 gateway Docker access and candidate private-key mounts require deployment-specific review.

## Licensing and attribution

The preserved GPL v3 text matches the inspected SEED checkout's `LICENSE.txt`. This establishes the upstream license text. Upstream-derived material needs appropriate attribution, retained notices and applicable source and modification obligations. The three Aiken manifests declare Apache-2.0 and the existing license text is retained. Preserve applicable notices and identify modifications to any Apache-covered source that is distributed. Cardano binaries remain external dependencies. A file-level provenance and permission decision for project-owned code and documentation, author credits and approved USI wording remain with the project rightsholders. No license was added or changed during this phase. [Attribution and existing notices](../../NOTICE.md), [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Publication recommendation

B11 passed the [controlled runtime check](b11-runtime-result.md). B12–B16 are presented at their historical and offline evidence levels, with the new B15/B16 deployment automation marked offline-validated. Further runtime work is outside the current publication scope. The [publication checklist](../reproducibility/publication-checklist.md) records the rights, attribution and approval gates.

The original project evidence stays outside the release. The clean source-only Git checkout is prepared for local review with independent history. No remote is configured.
