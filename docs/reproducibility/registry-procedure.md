# Deploy and operate the B15 v2 and B16 registry

Run this procedure in a fresh copy on a dedicated lab VM after approval for runtime work. These commands are intended for magic 5556 in the selected publication experiment. The deployment helpers passed offline checks. Transaction balancing, submission, confirmation and network changes require a live run.

## 1. Initialize the network and build the blueprint

Follow the experiment README and confirm AS180–183 are advancing on a common chain. Keep the original generated default-deny policy. Record the baseline controller rules and candidate traffic before submitting any registry transaction.

Run from the repository root. The example selects B15; set `experiment=experiments/B16-cardano-did-authentication` for B16.

```bash
umask 077
experiment=experiments/B15-cardano-smart-authorization-v2
(cd "$experiment/relay-authorization" && aiken check && aiken build)
funding_prefix="$experiment/network/config/generated/testnet-conway-v2/utxo-keys/utxo1/utxo"
registry() {
  python3 scripts/deploy-registry.py "$experiment" --funding-key "$funding_prefix" "$@"
}
registry wallet
registry funds
```

The helper derives a payment address from the specified funding verification key and generates a distinct administrator key under `network/.runtime/registry-private/`. Verify the address has a confirmed pure-ADA UTXO. If the generated wallet is not funded on the running chain, provision a funded payment key pair locally and set `funding_prefix` to its common filename without the extension **before** applying parameters. Keep both signing keys on the host. The B16 Ed25519 authority is a separate key.

## 2. Prepare collateral and bind the scripts

Select `split_input` from `registry funds` as a confirmed pure-ADA reference with sufficient balance. Use a collateral amount appropriate for the live protocol and script execution costs. The example requests 5 ADA. The first transaction command builds only and reports its ID.

```bash
registry collateral --input "$split_input" --lovelace 5000000
registry collateral --input "$split_input" --lovelace 5000000 --submit
registry funds
```

Wait for confirmation. Set `collateral_ref` to the confirmed output selected for collateral, and `mint_input` to a **different** funded output. Confirm both references in `registry funds`. Keep collateral unspent for the mint and subsequent transitions.

```bash
registry prepare --input "$mint_input"
```

The script applies the mint policy to the new output reference, calculates the policy ID with Cardano CLI and checks it against Aiken. It applies the membership validator to the administrator hash, applied policy ID and token name. It writes the text envelopes and controller inputs under `network/deployment/registry/`. Keep that directory with its deployment. The helper refuses to overwrite it, including a partially prepared deployment. Review any partial output before preparing a fresh copy.

## 3. Mint and lock the registry NFT

```bash
registry mint --input "$mint_input" --collateral "$collateral_ref" --lovelace 5000000
registry mint --input "$mint_input" --collateral "$collateral_ref" --lovelace 5000000 --submit
registry verify --revision 0
```

The mint transaction consumes the applied one-use input, uses integer redeemer 0, creates one `B15_REGISTRY` and locks it at the applied validator with the AS184 datum at revision 0 and authorization false. Adjust the output ADA if the CLI reports a minimum-output requirement. If a verify command reports a missing or disagreeing output immediately after submission, wait and check again. If submit has an uncertain outcome, query the ledger before trying to spend the inputs again.

The CLI builds in the selected incumbent container using its live socket. The unsigned transaction travels to the host for signing. Only the signed transaction returns for submission. The build-only and submit commands each construct a body from the current chain state. For evidence, retain the printed IDs and confirmed registry response in the private run log.

## 4. Authorize, authenticate and admit

Choose a fresh pure-ADA fee input from `registry funds`, different from collateral. Set `fee_input` to its confirmed reference.

```bash
registry authorize --input "$fee_input" --collateral "$collateral_ref"
registry authorize --input "$fee_input" --collateral "$collateral_ref" --submit
registry verify --revision 1
```

The helper queries all four incumbents for revision 0 before building. It preserves the registry asset and ADA at the script address, makes a revision-1 authorized datum, requires the administrator signature and also signs with the fee key. The [datum and action schema](genesis.md#b15b16-registry-data) lists exact fields and constructor indices.

### B15 v2

```bash
(cd "$experiment/network" && python3 scripts/admission_controller.py)
(cd "$experiment/network" && python3 scripts/enforce_admission.py)
(cd "$experiment/network" && python3 scripts/enforce_admission.py --apply)
```

The first command evaluates registry state. The second checks it and verifies expected AS183 firewall state in dry-run mode. Apply only after confirming revision 1, rule order and baseline traffic. The enforcer removes AS183's targeted AS184 TCP/3001 DROP rules. B15 has no DID challenge.

### B16

The staged deployment runs both Python processes on the trusted Linux VM, each using its Cardano container's existing network namespace. It requires root access for `nsenter`, `ip`, Docker access for the gateway, and a Python interpreter with cryptography under `sudo`. Define the helper and stage the roles as the experiment operator. Stage before the live phase if desired.

```bash
sidecars() {
  python3 scripts/deploy-b16-sidecars.py "$experiment" "$@"
}
sidecars stage
roles="$experiment/network/.runtime/did-deployment"
python3 "$roles/candidate/scripts/did_auth/identity.py" AS184
sidecars publish-identity
env -u CARDANO_EXPERIMENT_RUNTIME python3 "$roles/authority/scripts/did_auth/create_authority.py"
env -u CARDANO_EXPERIMENT_RUNTIME python3 "$roles/authority/scripts/did_auth/enrollment.py" issue
python3 "$roles/authority/scripts/did_auth/enrollment.py" verify
sidecars publish-enrollment
sidecars publish-registry
```

The authority's encrypted private key stays in its own role directory. The candidate private key stays in the candidate role directory. Only the public record, certificate and authority verification key are distributed, and the gateway receives the registry address and policy ID. Publishing uses fresh destination paths. Role directories are owner-only file staging within one trusted VM. VM root retains access to all directories.

Once revision 1 is verified, run the following from the repository root in **separate terminals**. Set `experiment` to the B16 path in both. Start the candidate after the gateway prints its ready line. The gateway serves one session and exits. The namespace launcher checks the container is running and owns the expected IP.

```bash
# AS183 terminal
sudo python3 scripts/deploy-b16-sidecars.py "$experiment" gateway

# AS184 terminal
sudo python3 scripts/deploy-b16-sidecars.py "$experiment" candidate
```

AS184 sources the connection from `10.184.0.71`. AS183 listens at `10.183.0.71:4040` and checks source address, identity, certificate and challenge response before requiring live registry agreement. The order and checks in the gateway are unchanged. The helper requires both `ALLOW` and `GRANTED` as well as authentication. TCP/3001 remains denied until the local firewall controller inserts the AS184 exception. AS185 has no issued candidate certificate, signing material or admission rule. Confirm the AS185 TCP/3001 denial and protected rule order as a separate control. TCP/4040 and TCP/3001 are independent ports. The controlled gateway's protocol has no TLS or independent cryptographic proof of gateway identity to the candidate.

## 5. Revoke, enforce and collect evidence

Select a current pure-ADA fee input instead of reusing a consumed one. Keep the original collateral if it remains unspent.

```bash
registry funds
registry revoke --input "$fee_input" --collateral "$collateral_ref"
registry revoke --input "$fee_input" --collateral "$collateral_ref" --submit
registry verify --revision 2
```

Set `registry_utxo` from the confirmed revision-2 query for B16. Verify the applicable dry run before applying the phase-specific firewall change:

```bash
# B15 v2
(cd "$experiment/network" && python3 scripts/enforce_revocation.py)
(cd "$experiment/network" && python3 scripts/enforce_revocation.py --apply)

# B16
(cd "$experiment/network" && python3 scripts/b16_n17_revocation_controller.py --expected-utxo "$registry_utxo")
(cd "$experiment/network" && python3 scripts/b16_n17_revocation_controller.py --expected-utxo "$registry_utxo" --apply)
```

B15 reinstalls candidate DROP rules. B16 removes candidate ACCEPT overrides and retains the two baseline DROP policies. Record exact revisions, confirmed references, controller and gateway output, rule order and counters, candidate and legitimate peer tips, and matched TCP/3001 captures. For B16 record TCP/4040 endpoint observations separately. Verify a fresh candidate connection after revocation and continued legitimate peer traffic. Use the [runtime verification plans](runtime-verification.md) to stop the isolated experiment and keep evidence local.
