# Security review

The authoritative experiment trees contain private KES, VRF, wallet, genesis, administrator and DID credential material. A filename-only census found 490 `.skey`, 92 `.key` and three `.pem` files across those trees, including generated outputs. The pre-existing workspace copies contain build contexts, binaries and deployment artifacts. The absence of those file extensions in a copy cannot establish that a generated context is clear of secrets. Treat the bulk inventory and raw deployment copies as research material. They were preserved under owner-accessible `.local-research/`, ignored from the release root. The protected workspace metadata directories and authorized research originals are outside the release review. Git reports no repository and the existing `.git` directory is empty, so there is no workspace history to scan.

| Item | Publication status | Review point |
|---|---|---|
| Producer, genesis, wallet, administrator and DID private files | Excluded | Generate fresh per run. A dedicated build context contains producer signing keys after compilation. Keep its images out of registries. |
| Databases, logs, raw captures, transaction records, Docker contexts and binary archives | Excluded | Review any proposed sample for sensitive payloads or persistent identifiers. |
| Historical addresses and registry references | Excluded from deployment config | Controllers receive fresh values via deployment files or, for the B16 revocation UTXO, an explicit parameter. |
| B16 adverse live network probes and their dedicated test gateway | Preserved in the private research copies | The release documents historical outcomes and retains local verification checks. |
| Public crypto fixtures and policy constants | Included where reusable | Aiken test fixture hashes and the synthetic B12 digest are public test data. |
| Path defaults | Reviewed | Network build defaults use local `.runtime/`; optional runtime override can deliberately redirect storage. |
| Credentials embedded in release files | Static pattern scan | See matrix. Pattern matching has limited coverage of encoded or unfamiliar formats. Stage a fresh reviewed file list and scan again before any commit. |

No credential values are reproduced in this report. Keep the working directory uncommitted pending review, and use only the reviewed release paths in an independent checkout.

## Final release index review

The local publication checkout was assembled from the explicit source paths. The final review checked tracked filenames and file contents, credential patterns, symlinks, executable binary formats, backups, generated state and ignored index entries. Operational absolute paths in the B11 audit point to private evidence or to commands from that run. Active source paths are relative to the experiment, configurable local roots, or intended container paths. The private archive, captured traffic, signing material and deployment build products stay outside the checkout.

Upstream license texts and Aiken declarations are retained. The final release is gated on rights and attribution confirmation. The [publication checklist](../reproducibility/publication-checklist.md) records the required approval steps.
