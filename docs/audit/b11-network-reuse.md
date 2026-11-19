# B11 external network compatibility gate

The operator ran the read-only checker in the Ubuntu terminal and reported a successful check for all 22 historical networks. The external-network candidate was emitted. Local inspection confirmed that all 38 service definitions were unchanged and that each network maps to the corresponding `output_` network. Compose 1.27.4 accepted the file. This execution environment still lacks daemon access. The operator subsequently launched B11 and collected the [runtime evidence](b11-runtime-result.md). The commands below record that case.

## Read-only check in the Ubuntu terminal

```bash
cd /home/seed/cardano-seed-emulator-experiments
out=/tmp/b11-runtime.ZdMSRhh0/B11-cardano/output
python3 scripts/check-b11-network-reuse.py \
  "$out/docker-compose.isolated.yml" "$out/docker-compose.external.yml"
```

Use the Python environment with PyYAML from the SEED setup. The helper reads Docker network, container attachment and image metadata without saving complete container inspection output. It requires one exact local bridge per subnet, the expected gateway and IPAM settings, MTU and other driver options, matching stopped historical Compose service/static IPv4 assignments, and no occupied or retained endpoints. The generated B11 config leaves gateway selection to Docker. The check uses the first usable address for that bridge default. An empty or ambiguous attachment history fails the check conservatively. A stopped container's configured future static address can match the same B11 service slot if its live address and endpoint are clear. Keep the historical projects stopped while sharing their networks.

A successful check writes a separate Compose file with only the network declarations replaced by external names. Use this file by itself because external definitions accept no IPAM or driver settings from the generated file. The service attachments, static IPs, topology and genesis are preserved. Compose will reuse the existing networks and will fail if they are absent. [Docker Compose external networks](https://docs.docker.com/reference/compose-file/networks/#external)

## Conditional launch

After the read-only check exits zero, inspect the reported mappings and validate the new file. Use the following commands only with launch approval. Namespaced images and containers are preserved. Image builds may add layers to the shared daemon cache.

```bash
cd /tmp/b11-runtime.ZdMSRhh0/B11-cardano/output
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml config -q
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml build 39e016aa9e819f203ebc1809245a5818 98a2693c996c2294358552f48373498d
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml build
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml up -d --no-build
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml ps
```

After evidence collection, use `docker-compose -p b11verifyzdmsrhh0 -f docker-compose.external.yml stop` from the output directory. This targets the B11 verification project.

If the read-only check identifies an incompatible network or held endpoint, preserve the historical daemon state. Use a dedicated disposable Ubuntu VM with its own Docker daemon and the existing B11 run-only Compose definition. This preserves the 22 subnets and avoids changing historical resources.
