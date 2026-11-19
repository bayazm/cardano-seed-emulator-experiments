# Installation

The audited host reports Ubuntu 20.04 Docker packages, Python 3.8.10, Docker 20.10.21 and standalone Compose 1.27.4. The experimental launchers currently support x86-64 Linux with `amd`. Use a dedicated emulator host. Docker access and privileged emulator containers require host administrative trust. Install GNU Bash, coreutils, tar, curl, and Python 3 with venv support. Install tshark or tcpdump for optional capture analysis. The Docker contexts declare additional Linux node tools, including iptables where applicable.

## SEED Emulator

Install the exact inspected source revision in an independent checkout outside this repository. The checkout identifies as `v1.1-2-ga8d93cd6`; its Python package declares version `0.0.7`.

```bash
git clone https://github.com/seed-labs/seed-emulator.git seed-emulator
cd seed-emulator
git checkout a8d93cd65aace99a454fae44895d41d7e8cd8197
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -c 'from seedemu import Emulator, Platform; print(Platform.AMD64)'
```

The pinned checkout declares requests 2.22.0, PyYAML 6.0.1, web3 5.31.1, eth_account 0.5.9 and eth-rlp below 0.3. Fresh dependency resolution remains unverified. For B16 install `cryptography`; local validation uses 2.8 and does not establish a minimum or a supported modern version. The optional sidecar uses Ubuntu 22.04 and distro python3-cryptography. Use the upstream requirements and record the resolved dependency set.

## Cardano binaries

Run these commands in one experiment's compiler directory from its README. For B11 select 11.0.1; select 11.1.3 for B12–B16. The local binaries report CLI 11.0.0.0 and 11.2.3.0 respectively. Keep the tarball in an external download directory or an ignored directory.

```bash
version=11.1.3
archive="cardano-node-${version}-linux-amd64.tar.gz"
case "$version" in
  11.0.1) expected=40e88a543564251338c4888ef79fde51d2306c18b48ac308c9eab3220e3a13f0 ;;
  11.1.3) expected=530fb99986fbdccc46f9ee0dd86cabb1393b015feac9173cb731d89fa748365f ;;
esac
curl -fL -o "$archive" "https://github.com/IntersectMBO/cardano-node/releases/download/$version/$archive"
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
mkdir -p resources/cardano-static
tar -xzf "$archive" -C resources/cardano-static
resources/cardano-static/bin/cardano-node --version
resources/cardano-static/bin/cardano-cli --version
```

Archive digests are from the official release assets. The local B12 archive independently matched 11.1.3. The local B11 archive was unavailable for comparison. [11.0.1 release assets](https://github.com/IntersectMBO/cardano-node/releases/expanded_assets/11.0.1), [11.1.3 release assets](https://github.com/IntersectMBO/cardano-node/releases/expanded_assets/11.1.3)

## Aiken

Install Aiken v1.1.24 for the host and confirm with `aiken --version`. Each contract source pins standard library v4.0.0 and targets Plutus V3. From its manifest directory run `aiken check` for tests and `aiken build` for a fresh blueprint. Blueprint application depends on current deployment parameters. [Aiken v1.1.24 release](https://github.com/aiken-lang/aiken/releases/tag/v1.1.24)
