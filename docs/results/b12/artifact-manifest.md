# B12 evidence artifact manifest

All 108 Phase 6C evidence references are accounted for below. Repeated references share an entry. The archive ID identifies the source of an observation or public extract.

- `RUN_4242` is the operator's original run. `EARLY_BUILD` is the early compilation workspace. `RESEARCH` is the private research archive. Locations are relative to these custodian-controlled roots.
- File SHA-256 values are from a direct Phase 6D read. Directory entries identify available local manifests and otherwise have no aggregate checksum. A file digest identifies the archived bytes. The reproduction report provides the experimental verification status.
- Local-only material stays private. Sanitization-required files need content review before release. The public-inclusion-suitable version outputs are summarized in the report. The sanitized extracts have their own [checksums](SHA256SUMS).

| ID | Archive location | Disposition | Phase 6D availability / source SHA-256 | Uses |
| --- | --- | --- | --- | --- |
| <a id="e001"></a>E001 | `RESEARCH/b12-p9-sequential-live/b12-p9-genesis-manifest.json` | Sanitization required | Present · `f95373606c81604e6b25c8186593f7c80861b437247e50a59f422cc49f0ce652` | 2 |
| <a id="e002"></a>E002 | `RESEARCH/b12-phase-6a/old-db-history-recheck.json` | Sanitization required | Present · `2d141c46ba3348566d16c62127ade171038d47c5116d38666b764eec5a5c3b9e` | 3 |
| <a id="e003"></a>E003 | `RESEARCH/b12-recovery.neooblh8/p9-quiescent-transactions.json` | Local only | Present · `eb92804c0a0754a291077483a4f3faa0aa13f204a0972690a25b33936ed994ee` | 1 |
| <a id="e004"></a>E004 | `RESEARCH/b12-recovery.neooblh8/p9.sha256` | Sanitization required | Present · `a810d15b478ff48fda75c9077170bdec4811d82b697b26e8cad9105d6c392ddb` | 1 |
| <a id="e005"></a>E005 | `RESEARCH/b12-recovery.neooblh8/old-common-block.json` | Sanitization required | Present · `3d32bd44ecd3ca02352eaa3c4b27044695e67de91f8e5b1b944e73f6cef59bdf` | 1 |
| <a id="e006"></a>E006 | `RESEARCH/b12-recovery.neooblh8/old-restored-history.json` | Sanitization required | Present · `b94fe870b2aa13aad4e1609095b2a752ec70f1d12607415013dae3ef52985b53` | 1 |
| <a id="e007"></a>E007 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/cutover-verification.md` | Sanitization required | Present · `e56fa70e951c20883995755318fedb55b69ca04405b643520c4c92de5f3fb8e4` | 4 |
| <a id="e008"></a>E008 | `RESEARCH/b12-4242-preservation/SHA256SUMS` | Sanitization required | Present · `6c326afedb7b95b3c740b438967190a72c648bc91de39e3e39b69cc8691c40f7` | 3 |
| <a id="e009"></a>E009 | `RESEARCH/b12-4242-preservation/preservation.json` | Local only | Present · `c94a79a5cad96d02c2fe725ed5cbf330308bb0eea160ab3dca82bf6bf1aec5f8` | 1 |
| <a id="e010"></a>E010 | `RESEARCH/b12-p9-genesis-check/public-verification.json` | Sanitization required | Present · `75aeb58e9eab9f1a6941ce54c024494b8b81c9570e3f23f361751b32ca8630d6` | 1 |
| <a id="e011"></a>E011 | `RESEARCH/b12-4242-sequential-inventory` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e012"></a>E012 | `RESEARCH/b12-4242-sequential-inventory/p9-compose-static.yml` | Sanitization required | Present · `8df345d314a72c3f77f82a20059e5a76bb122c21399a455430b65e5d6674b57b` | 1 |
| <a id="e013"></a>E013 | `RUN_4242/runtime/evidence/phase-5d/protocol-compatibility/final-live/as150-node-version.txt` | Public inclusion suitable | Present · `660cedd69244c04771f8f7515f3fb456094a13c68ebe14fde753f9f0669210aa` | 1 |
| <a id="e014"></a>E014 | `RUN_4242/runtime/evidence/phase-5d/protocol-compatibility/final-live/as150-cli-version.txt` | Public inclusion suitable | Present · `e664f61afd32e34350b76febfb75fa4b8e44968d2ef95e22cc37da5cf903bb94` | 1 |
| <a id="e015"></a>E015 | `EARLY_BUILD/phase-2.diff` | Local only | Present · `57953dd2e6b1ebc02e97ed6be066ac6523bad09e26094a507bd6cfd4aa2bae80` | 1 |
| <a id="e016"></a>E016 | `EARLY_BUILD/compile.log` | Sanitization required | Present · `22805000c35b7ec177d75fd0cd264c5895e391c5a2222e9e88bf96031d77ede3` | 1 |
| <a id="e017"></a>E017 | `EARLY_BUILD/compose.resolved.yml` | Sanitization required | Present · `4cfa352f25e886aabc5c1c5d1e8661000cc10bd2f03d08fac029f251153c730c` | 1 |
| <a id="e018"></a>E018 | `RUN_4242/experiments/B12-cardano/output/docker-compose.yml` | Sanitization required | Present · `afac39cef5fcc38d16a197a07caeba134ab2b3c8ad50669208f7e8076530a24c` | 1 |
| <a id="e019"></a>E019 | `RUN_4242/runtime/evidence/deployment-compose.yml` | Sanitization required | Present · `403f4382eabc7b661f704ad588ae2d6a6dbb154cad5b42a9889d3fe307c8ed3d` | 2 |
| <a id="e020"></a>E020 | `RUN_4242/runtime/evidence/build.log` | Sanitization required | Present · `af50e53276c6b32117cf6b046bdf359b7871f073a2f4cfe1b7ac3d63cb780e62` | 1 |
| <a id="e021"></a>E021 | `RUN_4242/runtime/evidence/startup.log` | Sanitization required | Present · `285b295edd2f7f798f72a2001dfa276165f516c42e076859c25b62d1967107fb` | 1 |
| <a id="e022"></a>E022 | `RUN_4242/runtime/evidence/preflight.txt` | Sanitization required | Present · `003e36c5502ea7a6b9785c8eec48ed2e81b5396e9a8ea7b97c972541373591b4` | 1 |
| <a id="e023"></a>E023 | `RESEARCH/b12-4242-preservation/public-config` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e024"></a>E024 | `RUN_4242/runtime/evidence/phase-5d/protocol-compatibility/host-genesis.sha256` | Sanitization required | Present · `89e23f4cec1ceaf5953d229aae8d7ec624dbe0c020fb4d4153e10f4f6757e3a2` | 1 |
| <a id="e025"></a>E025 | `RESEARCH/b12-p9-sequential-live/config/private-testnet-conway-v2` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e026"></a>E026 | `RESEARCH/b12-p9-sequential-live/compose-normalized.yml` | Sanitization required | Present · `92b50f0bb293d7fdeea351e3428e5cb55b9cbb129d42706d35ae61ee578a4ee7` | 1 |
| <a id="e027"></a>E027 | `RUN_4242/runtime/evidence/phase-4b-verification.md` | Sanitization required | Present · `70db090857775ed494076bd2e995797e7a91c94fa8cc215482c4a9d49ce7b0c9` | 2 |
| <a id="e028"></a>E028 | `RUN_4242/runtime/evidence/phase-4b-20261119T172456Z.461nC5V4` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e029"></a>E029 | `RUN_4242/runtime/evidence/phase-4b-20261119T172613Z.sEfiWVh4` | Local only | Directory present. No aggregate checksum. | 2 |
| <a id="e030"></a>E030 | `RUN_4242/runtime/evidence/phase-4b-postgenesis-20261119T181003Z-jvhk3zc9` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e031"></a>E031 | `RUN_4242/runtime/evidence/phase-5a/phase-5a-verification.md` | Sanitization required | Present · `ffdbdf7fc64890cc963fc0c5a19863d50cd2eb89c6758d2f1fcd9609b3566e43` | 2 |
| <a id="e032"></a>E032 | `RUN_4242/runtime/evidence/phase-5a/prepared-20261119T182342Z/wallets.json` | Local only | Present · `066f9632fdb6ff8e9dba4c8368f7e66dd1f3c7c1fc031668e65bf1aed1541f2c` | 1 |
| <a id="e033"></a>E033 | `RUN_4242/runtime/evidence/phase-5a/prepared-20261119T182342Z/validation.json` | Sanitization required | Present · `7d414dc759f08c234fa3991ceaf6e837699ef2a642cba6993c497c8805e24d8c` | 1 |
| <a id="e034"></a>E034 | `RUN_4242/runtime/evidence/phase-5a/prepared-20261119T182342Z/submission/confirmation-summary.json` | Sanitization required | Present · `ff7e97ae50655d96eea3a5e1378ceca6136b046e970fb37b30eeb45b6ffc2a92` | 1 |
| <a id="e035"></a>E035 | `RUN_4242/runtime/evidence/phase-5b/phase-5b-verification.md` | Sanitization required | Present · `8176b0646ff0948b8e4c51bc3b3f0d0ec4058138a831c8a8c10d9c47a389fdb7` | 2 |
| <a id="e036"></a>E036 | `RUN_4242/runtime/evidence/phase-5b/prepared-20261119T184939Z/block-135.cbor` | Local only | Present · `81b538a011b822ae4338db72810307ac41a5f6f56053497c8ec7f7bcdf4feb71` | 1 |
| <a id="e037"></a>E037 | `RUN_4242/runtime/evidence/phase-5b/prepared-20261119T184939Z/block-135-verification.json` | Sanitization required | Present · `4d9aceec0e5d5342c708ff3fcc5700859da79e97ff301eca75d3ae6fb9226113` | 1 |
| <a id="e038"></a>E038 | `RUN_4242/runtime/evidence/phase-5b/prepared-20261119T184939Z/sensor` | Local only | Directory present. No aggregate checksum. | 2 |
| <a id="e039"></a>E039 | `RUN_4242/runtime/evidence/phase-5c/phase-5c-verification.md` | Sanitization required | Present · `ccba23d8163d640f25bb5b069878e8a5a8f38a884b4aa1911264ab6fcd1093d0` | 1 |
| <a id="e040"></a>E040 | `RUN_4242/runtime/evidence/phase-5c/trial-plan.csv` | Local only | Present · `bf2920af7e127417696b66e7e0a28b7575aa20b8a40608063f7afc8ea76a52eb` | 1 |
| <a id="e041"></a>E041 | `RUN_4242/runtime/evidence/phase-5c/trials.csv` | Sanitized public extract | Present · `77ce68b654a2f863b27aeadba291a2b35a0d027161f99eee19f79efd7f5cb624` · [Public extract](benchmark-trials.csv) | 3 |
| <a id="e042"></a>E042 | `RUN_4242/runtime/evidence/phase-5c/summary-statistics.json` | Sanitized public extract | Present · `3c1cb50326ce60228b5b94385701fa28abc8d5274b9d6e09af8b40ed2f647514` · [Public extract](benchmark-summary.json) | 2 |
| <a id="e043"></a>E043 | `RUN_4242/runtime/evidence/phase-5c/trials` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e044"></a>E044 | `RUN_4242/runtime/evidence/phase-5c` | Local only | Directory present. Local manifest fixtures.sha256 | 1 |
| <a id="e045"></a>E045 | `RUN_4242/runtime/evidence/phase-5d/phase-5d-verification.md` | Sanitization required | Present · `6103d61242f178a2ca0c0f366d6df71a4c3fe927a59b9436db71a88dadf5ee3a` | 2 |
| <a id="e046"></a>E046 | `RUN_4242/runtime/evidence/phase-5d/cli-cost-positive.log` | Sanitization required | Present · `97c6bd1cd9fd044effcbf0ae3353777283d98e04bc80be9218d33ffa77eef2c9` | 1 |
| <a id="e047"></a>E047 | `RUN_4242/runtime/evidence/phase-5d/cli-v9-cost-positive.json` | Sanitization required | Present · `9c3d43c62f34bcf0785fd3e329d30017cac40f50010504b3963e8f4adb04a129` | 1 |
| <a id="e048"></a>E048 | `RUN_4242/runtime/evidence/phase-5d/protocol-compatibility-investigation.md` | Sanitization required | Present · `89617a5aa27daadd9cfc6cfcff2307085d357d4f9aeaf81cfc197b2b9afebf97` | 2 |
| <a id="e049"></a>E049 | `RESEARCH/b12-4242-cutover-backup/pre-stop-history.json` | Sanitization required | Present · `2d141c46ba3348566d16c62127ade171038d47c5116d38666b764eec5a5c3b9e` | 1 |
| <a id="e050"></a>E050 | `RESEARCH/b12-4242-cutover-backup/quiescent.sha256` | Local only | Present · `cd9491fcd1d24218ad1d549c529187d2ffaac961b1be351406527598e46423ca` | 1 |
| <a id="e051"></a>E051 | `RESEARCH/b12-4242-preservation/canonical-evidence-blocks` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e052"></a>E052 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/verification.json` | Sanitization required | Present · `14d77fd9479f084fa8531a14912370acc7277b4af4014da0ee4e1bdbc253da64` | 1 |
| <a id="e053"></a>E053 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/protocol-parameters.json` | Sanitization required | Present · `4be557c7339677c062309775035878ec012ac9e80476c3776351b88895b3b85a` | 1 |
| <a id="e054"></a>E054 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/source.sha256` | Sanitization required | Present · `908e1fa9e24ff2c4e65428e50075a263b497349941785ad50d2a5ff04dfd7202` | 1 |
| <a id="e055"></a>E055 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/aiken-version.txt` | Public inclusion suitable | Present · `99d9540d240503d1b1465d0d52c27f0653688c08c1e63a67f4db1361571b5a9c` | 1 |
| <a id="e056"></a>E056 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/aiken-check.log` | Sanitization required | Present · `df9eba58fda0ba195a42ab6ac8410c0dbdfbffff2f8a9fbb96f983b32970ccec` | 1 |
| <a id="e057"></a>E057 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/aiken-build.log` | Sanitization required | Present · `2a804b9bf7c930bf11b9995b8863df7b7ca5402596b3332ec1326dd96a5e8003` | 1 |
| <a id="e058"></a>E058 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/project/plutus.json` | Sanitization required | Present · `1d5d2c0c299a622394788eb07eff43b466c5a8cbc22a0acaf8d063c36b3a5d57` | 1 |
| <a id="e059"></a>E059 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/phase-5d-p9-preparation.md` | Sanitization required | Present · `33962bdc8e49ec37a5d35bcd0ffe9d15c71a0fedbc41950f2cd14c39a60603ea` | 2 |
| <a id="e060"></a>E060 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/funding-validation.json` | Sanitization required | Present · `12a1a2bea319fa7aaba9db4c0cb60be59eee56762e3c39fef63a987bc3fdebdc` | 1 |
| <a id="e061"></a>E061 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/funding-confirmation-summary.json` | Sanitized public extract | Present · `e3b79a4130956ecf7617191d1b3148a546d293eef693d228586117e73a2862ea` · [Public extract](p9-inclusion-summary.json) | 1 |
| <a id="e062"></a>E062 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-cost-live.json` | Sanitization required | Present · `eae9031288a1b9aa8b8c508c36b12ccb54f8747c92b206f81d926ae946974bab` | 1 |
| <a id="e063"></a>E063 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-signed-validation.json` | Local only | Present · `2ec2103947bda40c16d8edd8594ddd9b985a88a654c3d8f359c7cf72d4f3d3ce` | 1 |
| <a id="e064"></a>E064 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-confirmation-summary.json` | Sanitized public extract | Present · `27e7d44ed84f60d6d65895512d0c7e6bc14abee1d3283a1017cb55d36684cd34` · [Public extract](p9-inclusion-summary.json) | 1 |
| <a id="e065"></a>E065 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-on-chain-script.json` | Sanitization required | Present · `143e07f977cf62a7664d212cc0765f452571121c73d5c72a1a4600e5a8bb7e1b` | 1 |
| <a id="e066"></a>E066 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/negative-results.json` | Sanitization required | Present · `f671d5f6feae18bc14963fcf735652eaab4d4441a957eafbaf19b4ade3309573` | 1 |
| <a id="e067"></a>E067 | `RUN_4242/runtime/captures` | Local only | Directory present. No aggregate checksum. | 1 |
| <a id="e068"></a>E068 | `RUN_4242/runtime/evidence/phase-4b-postgenesis-20261119T181003Z-jvhk3zc9/as150-net0-pcap.sha256` | Local only | Present · `2d885cf853fa81bc67250eb9b7ce18eee80b2c1fea014f052aa7f11df47df438` | 1 |
| <a id="e069"></a>E069 | `RUN_4242/runtime/evidence/phase-4b-postgenesis-20261119T181003Z-jvhk3zc9/as153-net0-pcap.sha256` | Local only | Present · `d00dd492c46079ba424c9d88820ec0cc0e60d5eff1756a3619ccee36585edbaa` | 1 |
| <a id="e070"></a>E070 | `RUN_4242/runtime/evidence/phase-5c/pcap` | Local only | Directory present. Local manifest captures.sha256 | 1 |
| <a id="e071"></a>E071 | `RUN_4242/runtime/evidence/phase-5c/pcap/captures.sha256` | Local only | Present · `87dc221a70af34e87e8fd8626594bfd9d0c3532a43b8e3705738ae6cca989f75` | 1 |
| <a id="e072"></a>E072 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/capture-summary.json` | Sanitization required | Present · `8508cbe2ece1117767c0f4482dec3ef313dea8b6964a400f24cc6fcf1d69ad37` | 1 |
| <a id="e073"></a>E073 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/pcap.sha256` | Local only | Present · `ad4c20c4bc335a373add0cc5b423d6079d7ade6405d00a752f58fa4a0117f9f8` | 1 |
| <a id="e074"></a>E074 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/funding-captures.json` | Local only | Present · `16c83876852b5315d52a05c7f0c3bde4c9cc1c61ce0c10bc990fd2c4803af8db` | 1 |
| <a id="e075"></a>E075 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/funding-pcap.sha256` | Local only | Present · `277a1f69c660f65402bdec8f1bb6ab158b63d50ed426d6577ae3f3c5f442ab9c` | 1 |
| <a id="e076"></a>E076 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-captures.json` | Local only | Present · `32974d04d712bba90335f650e47bd48f1ae16d80b845427932f3abdff479e840` | 1 |
| <a id="e077"></a>E077 | `RESEARCH/b12-p9-sequential-live/.runtime/evidence/phase-5d-p9/authorized-run/spend-pcap.sha256` | Local only | Present · `c6397d48765abfa37195d6b1928613230e9d74ffa99c14dde5b40a6fa20395c4` | 1 |
| <a id="e078"></a>E078 | `RESEARCH/b12-phase-6a/transactions.csv` | Sanitized public extract | Present · `bea4db2e6c98ca9cb7d8a94a3923c44c03bbb8af64481d559bc1963fc9260ec4` · [Public extract](transaction-anchors.csv) | 3 |
| <a id="e079"></a>E079 | `RESEARCH/b12-phase-6a/audit-results.json` | Sanitized public extract | Present · `079eecea770a73c4ed1f51f529a35e7c7082a4ad227f3b60856d1fa66a289bb8` · [Public extract](audit-summary.json) | 3 |
| <a id="e080"></a>E080 | `RESEARCH/b12-phase-6a/audit.py` | Sanitization required | Present · `375139df595aed6f724ceccf6a5050ff22042d89ba6820db7edddfbd7b87931c` | 1 |
| <a id="e081"></a>E081 | `RESEARCH/b12-phase-6a/p9-db-block-recheck.json` | Sanitization required | Present · `ebf39ef12728ea673bba998035ac0d6ab2077bd535539243ae14714c8e8cbe9b` | 2 |
| <a id="e082"></a>E082 | `RESEARCH/b12-phase-6a/final-worktree.diff` | Local only | Present · `7c77925a5d95ebf8dea08ef2bdcf70b308452b94d00f64e19dd5d82242a420b4` | 2 |

## Missing historical sources

| Source | Disposition | Availability |
| --- | --- | --- |
| Original two-arm benchmark trial CSVs | Missing | No files or checksums were located. The public 30-row CSV is from the separate verified Phase 5C reproduction. |
| Standalone Phase 1 and Phase 3 reports | Missing | No files or checksums were located. The available early build artifacts are indexed above. |
