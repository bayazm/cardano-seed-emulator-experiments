# Operating the emulated networks

Run one experiment per dedicated Docker host or VM. Several variants share fixed interface addresses, Compose service names or container names. The commands use standalone `docker-compose` as observed on the audit host. With a Compose plugin use `docker compose` and first confirm `config -q` succeeds. Select the target by name from `docker-compose ps` before issuing any control command.

From the compiler directory specified in each experiment:

```bash
umask 077
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

The compiler writes under `output/` and may overwrite its previous output. Generate in a fresh experiment copy. It stages private producer keys in Docker build contexts and images, so keep both local. The default database and capture root is `.runtime/` beside the compiler, with an optional absolute `CARDANO_EXPERIMENT_RUNTIME` override. Select an empty path for a fresh run. Reuse an existing database only with its matching genesis and credentials. Docker commands require operator authorization for the target environment.

Use the actual container name and the experiment's testnet magic when querying from `output/`:

```bash
container=as150h-Cardano-Node-1-10.150.0.71
magic=4242
docker logs --tail 50 "$container"
docker exec "$container" cardano-cli query tip --testnet-magic "$magic" --socket-path /cardano/node.socket
docker exec "$container" ss -tn
```

Repeat tip queries over time and across expected peers. Record epoch, block, slot, tip hash and sync progress where reported. Compare hashes at a common slot or height if tip updates race. Also query the relevant ledger UTXO after a transaction or registry transition. A listening socket or successful TCP connection establishes transport reachability. Cardano handshake, common blocks and ledger queries address different layers.

## Packet capture

On the same fresh run, capture from a generated Cardano container and save only inside the ignored runtime capture directory. The compiler mounts that directory as `/captures` where applicable. Confirm `docker exec "$container" ip -br addr` and the mount before using these commands.

```bash
docker exec "$container" timeout 30 tcpdump -i net0 -nn -s 96 -w /captures/peer-phase.pcap 'tcp port 3001'
tshark -n -r "$capture_dir/peer-phase.pcap" -Y 'tcp.port == 3001' -T fields -e frame.time_relative -e tcp.flags
```

Set `capture_dir` to the host path mapped to `/captures` in the generated Compose file before running tshark. Record interface, clock, endpoint filter, duration, phase and capture drops. Compare matched windows and count SYN/SYN-ACK, resets, retransmissions and post-handshake traffic. An application handshake or ledger observation is needed to substantiate claimed synchronization. Review captures for payloads and identifying information before releasing any sample.

For disposable runs, `docker-compose stop` stops the selected project without deleting its data.
