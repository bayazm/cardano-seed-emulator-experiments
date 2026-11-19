# Validation matrix

Fresh genesis generation used the observed local CLI executables in isolated workspace copies. All nine copies produced role credentials and era hashes, compiled with the inspected SEED revision and passed standalone `docker-compose config -q`. Build contexts and private check artifacts reside in the ignored local review directory. Docker images and running networks were untouched.

| Experiment | Performed | Result and evidence | Remaining issue |
|---|---|---|---|
| B11 | Fresh genesis, Compose launch, node logs, repeated tips and TCP capture | Pass. Four nodes advanced from block 1 to 3 with matching tips. See [runtime result](b11-runtime-result.md). | Longer-run observation and separate ledger-state queries |
| B12 | Shared checks, Python helper argument parsing, synthetic digest and Aiken | Pass, sensor verifier and 3 Aiken checks | Fresh funding, ledger submission, confirmation and benchmark |
| B13 interoperability v2 | Shared checks with distinct magic | Pass, local logs and generated configuration | Handshake and ledger behavior in routed deployment |
| B13 node join | Shared checks with equal magic/time | Pass, local logs and generated configuration | Staged start and relay convergence |
| B13 same magic | Shared checks with equal magic and future stagger | Pass, local logs and generated configuration | Comparative startup and protocol behavior |
| B13 same time | Shared checks with equal magic/time | Pass, local logs and generated configuration | Cross-chain protocol and ledger behavior |
| B14 | Shared checks and offline historical PCAP TCP flag counts | Pass for config; aggregate flags reviewed | Live default-deny/admission/revocation and flow attribution |
| B15 v2 | Shared checks and Aiken | Pass, 23 Aiken checks | Fresh applied scripts, authorization/revocation transactions and controller enforcement |
| B16 | Shared checks, Aiken and local Ed25519 enrollment, integrated identity and registry-policy tests | Pass, 23 Aiken checks and local identity/policy tests | Fresh sidecar deployment, end-to-end authentication and admission/revocation |

The release static check covers Python compilation, JSON parsing, Bash syntax, local Markdown link targets and selected credential patterns. Docker Compose validation parses emitted config and cannot establish image availability, block production or protocol correctness. Aiken resolved its pinned dependency from the existing tool cache.

Final offline pass covered 41 Python files, 64 JSON files, five shell scripts and 27 Markdown files. The reviewed export directories contained zero binaries, symlinks, private credential files, raw captures or signed transaction bodies. Original file metadata fingerprints matched all eleven inspected directories.

The final publication review added an offline stage rehearsal and documented [runtime verification plans](../reproducibility/runtime-verification.md). The runtime status in the table is unchanged.

## B15/B16 deployment follow-up

| Component | Offline result | Pending live check |
|---|---|---|
| B15 and B16 Aiken | 23 checks each and blueprint builds passed. Synthetic output-reference and membership parameters applied successfully. Cardano CLI matched the applied policy ID and generated the script address. | Execution, fees and confirmed mint/update outputs on a fresh chain |
| Registry helper | Collateral, mint, authorize and revoke arguments exercised with mocked ledger access against CLI help. Datum and redeemer fixtures checked. Previous generated Shelley files contain the default wallet initialization entry. | Wallet funding in the live ledger, Docker exec/copy paths, collateral sufficiency, build/sign/submit and confirmation |
| B16 role deployment | Staging, enrollment issuance and verification, public-file distribution, gateway imports and candidate entry point passed. Private roles had separate owner-only credential files. | Actual namespace entry, TCP/4040 challenge, live policy and TCP/3001 enforcement/revocation |

## B11 controlled runtime preflight

Fresh genesis, isolated SEED compilation and raw/run-only Compose parsing passed. Docker daemon inventory failed with a socket permission error. Existing resource collisions could not be excluded, so the build and launch were skipped. Heights, relay synchronization, ledger consistency and TCP/3001 were not observed. The [preflight report](b11-runtime-preflight.md) records retained evidence, exact gated launch commands and targeted shutdown steps.

The operator separately ran the live inventory checker in the Ubuntu terminal. All 22 historical networks passed and an external-network file was generated. Local Compose parsing passed and all 38 service definitions matched the run-only variant. Container launch and ledger verification remain pending. See the [network reuse gate](b11-network-reuse.md).

The operator subsequently built and launched the external-network project. The supplied Compose status shows 36 workload containers up and both image-helper containers exited 0. This session could read the four newly populated B11 database directories, including the relay. The subsequent evidence collection verified matching producer and relay tips and TCP/3001 reachability. See the [runtime result](b11-runtime-result.md).
