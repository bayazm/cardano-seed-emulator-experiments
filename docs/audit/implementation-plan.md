# Implementation plan

The publication workspace is `/home/seed/cardano-seed-emulator-experiments`. The authoritative trees are the B11–B16 examples under the independent SEED Emulator checkout. The workspace Git directory is empty and Git reports no repository. Existing workspace copies include both superseded candidates and runtime artifacts.

1. Inventory original and workspace files by relative path and category and compare competing implementations.
2. Audit executable entry points, configuration and identity dependencies, runtime paths, licensing and available evidence.
3. Prepare an allowlisted release tree. Preserve the existing copies and keep credentials, generated artifacts and transaction-specific material outside the release tree.
4. Write experiment procedures, evidence and review documentation, with a specific blocker wherever a fresh deployment cannot be reconstructed.
5. Validate statically and compare original inventory metadata before and after. Leave Docker, Git and publication to a separately authorized step.
