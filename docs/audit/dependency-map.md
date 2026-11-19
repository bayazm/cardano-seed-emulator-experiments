# Dependency map

| Experiments | Published node config and topology | Runtime inputs |
|---|---|---|
| B11 | `config/private-testnet-d0`, nodes 1–4 | Four era genesis JSONs, three producer credential sets under `config/generated/testnet-02/pools-keys` |
| B12 | `config/private-testnet-conway-v2`, nodes 1–4 | Four era JSONs and three producers under `config/generated/testnet-conway-v2`; funded delegator keys for transfers, optional metadata JSON |
| B13 variants | `config/network-A` nodes 1–2 and `config/network-B` node 3 | Two four-era genesis sets and separate pool1 credentials under `config/generated/network-A` and `network-B` |
| B14 | `config/private-testnet-conway-v2`, nodes 1–5 | Same generation layout as B12, with iptables for relay isolation |
| B15 v2 | `network/config/private-testnet-conway-v2`, nodes 1–5 | Same generation layout as B12 under `network/`, plus administrator key, funded wallet/collateral and live registry |
| B16 | Same Cardano config layout as B15 v2 | B15 registry layers plus local DID private/public keys, signed enrollment, trusted administrator public key and candidate transport/identity mapping |

All launchers compile Compose and Docker build contexts, import binaries and producer credentials into the contexts and create host bind-mount directories. Containers use `/cardano/node.socket` and `/cardano/db`. B13–B16 control paths assume Linux userspace. See the installation and genesis guides for the exact verified versions and missing deployment automation.
