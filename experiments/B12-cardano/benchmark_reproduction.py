"""Run the approved B12 Phase 5C schedule against the existing private testnet."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import argparse
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

import cardano_transaction as b12
from block_proof import canonical_transaction, digest, envelope_body
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PEERS = ("150", "151", "152", "153")
AMOUNT = 2_000_000
PROFILES = {"B12-4242": (4242, 2), "B12-P9": (4343, 9)}
FIXTURES = Path(__file__).resolve().parent / "benchmark-fixtures"


def schedule():
    rows = []
    order = ("ABC", "BCA", "CAB", "ACB", "CBA", "BAC", "BCA", "CAB", "ABC", "ACB")
    for round_number, workloads in enumerate(order, 1):
        for position, workload in enumerate(workloads, 1):
            rows.append(dict(trial_id=f"T{len(rows) + 1:02}", round=round_number,
                             position=position, workload=workload, status="NOT_RUN"))
    return rows


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data, indent=2)+'\n')
    temporary.replace(path)


def query(peer, *args):
    return json.loads(remote(NODES[peer], 'query', *args, timeout=8))


def remote(node, *args, timeout=45):
    return b12.run(['docker', 'exec', node, 'cardano-cli', 'conway', *args,
                    '--testnet-magic', str(MAGIC), '--socket-path', '/cardano/node.socket'],
                   timeout=timeout)


def local(*args):
    return b12.run([CLI, *args])


def address(index):
    keys = KEYS/f'delegator{index}'
    return local('address','build','--payment-verification-key-file',keys/'payment.vkey',
                 '--stake-verification-key-file',keys/'staking.vkey','--testnet-magic',str(MAGIC))


def build(folder, trial, expected_input, sender, recipient, params):
    filename = {"A": None, "B": "cip20.json", "C": "sensor.json"}[trial["workload"]]
    fixture = FIXTURES / filename if filename else None
    expected_metadata = json.loads(fixture.read_text()) if fixture else None
    current = query("150", "utxo", "--address", sender)
    save(folder / "input-lookup.json", current)
    entry = current[expected_input]
    if entry["address"] != sender or set(entry["value"]) != {"lovelace"}:
        raise ValueError("Selected input is not a pure ADA sender output")
    input_value = entry["value"]["lovelace"]
    if input_value < AMOUNT + 3_000_000:
        raise ValueError("Selected input lacks the benchmark change reserve")
    prefix = f"/tmp/b12-5c-{RUN_ID}-{trial['trial_id']}"
    flags = []
    if fixture:
        b12.validate_metadata(fixture)
        b12.run(["docker", "cp", fixture, f"{NODE}:{prefix}.json"])
        flags = ["--metadata-json-file", prefix + ".json"]
    result = remote(NODE, "transaction", "build", "--tx-in", expected_input,
                    "--tx-out", f"{recipient}+{AMOUNT}", "--change-address", sender,
                    *flags, "--out-file", prefix + ".body", timeout=90)
    (folder / "build.log").write_text(result + "\n")
    body = folder / "tx.body"
    b12.run(["docker", "cp", f"{NODE}:{prefix}.body", body])
    signed = folder/'tx.signed'
    key = KEYS/'delegator1/payment.skey'
    local('conway','transaction','sign','--tx-body-file',body,'--signing-key-file',key,
          '--testnet-magic',str(MAGIC),'--out-file',signed)
    txid = b12.parse_txhash(local('conway','transaction','txid','--tx-file',signed))
    assert txid == b12.parse_txhash(local('conway','transaction','txid','--tx-body-file',body))
    view = json.loads(local('debug','transaction','view','--tx-file',signed))
    save(folder/'signed-view.json',view)
    assert view['era']=='Conway' and view['inputs']==[expected_input]
    decoded = {label:dict(pairs) for label,pairs in view['metadata'].items()} if view['metadata'] else None
    assert decoded == expected_metadata
    fee = int(view['fee'].split()[0])
    outputs = []
    for index, output in enumerate(view['outputs']):
        addr = output['address']
        value = output['amount']['lovelace']
        assert output['network']=='Testnet' and set(output['amount'])=={'lovelace'}
        raw = local('conway','transaction','calculate-min-required-utxo','--protocol-params-file',
                    ROOT/'protocol-parameters.json','--tx-out',f'{addr}+{value}')
        [minimum] = map(int,re.findall(r'\b\d+\b',raw))
        assert value >= minimum
        outputs.append(dict(ref=f'{txid}#{index}',address=addr,lovelace=value,min_lovelace=minimum))
    [payment] = [output for output in outputs if output['address']==recipient]
    [change] = [output for output in outputs if output['address']==sender]
    assert len(outputs)==2 and payment['lovelace']==AMOUNT and change['lovelace']==input_value-AMOUNT-fee
    [witness] = view['witnesses']
    public = bytes.fromhex(re.search(r'"([0-9a-f]+)"',witness['key'])[1])
    signature = bytes.fromhex(re.search(r'"([0-9a-f]+)"',witness['signature'])[1])
    [change_view] = [output for output in view['outputs'] if output['address']==sender]
    assert hashlib.blake2b(public,digest_size=28).hexdigest()==change_view['payment credential key hash']
    Ed25519PublicKey.from_public_bytes(public).verify(signature,bytes.fromhex(txid))
    encoded = bytes.fromhex(json.loads(signed.read_text())['cborHex'])
    minimum_fee = int(local('conway','transaction','calculate-min-fee','--tx-body-file',body,
                        '--protocol-params-file',ROOT/'protocol-parameters.json',
                        '--witness-count','1','--output-text').split()[0])
    size_fee = params['txFeeFixed']+params['txFeePerByte']*len(encoded)
    assert len(encoded)<=params['maxTxSize'] and fee>=max(minimum_fee,size_fee)
    facts = dict(txid=txid,input_ref=expected_input,input_lovelace=input_value,payment=payment,
                 change=change,fee_lovelace=fee,cli_min_fee_lovelace=minimum_fee,
                 signed_size_fee_lovelace=size_fee,signed_cbor_bytes=len(encoded),metadata=expected_metadata)
    save(folder/'construction.json',facts)
    return facts


def observe(peer, facts):
    before = query(peer,'tip')
    refs = [facts['input_ref'],facts['payment']['ref'],facts['change']['ref']]
    flags = [word for ref in refs for word in ('--tx-in',ref)]
    utxos = query(peer,'utxo',*flags)
    stamp = time.monotonic()
    wall = utc()
    after = query(peer,'tip')
    exact = refs[0] not in utxos and all(
        utxos.get(out['ref'],{}).get('address')==out['address']
        and utxos.get(out['ref'],{}).get('value')=={'lovelace':out['lovelace']}
        for out in (facts['payment'],facts['change']))
    return dict(peer=peer,utc=wall,monotonic=stamp,before=before,after=after,utxos=utxos,exact=exact)


def watch(folder, facts, started):
    pending = set(PEERS)
    found = {}
    cycle = time.monotonic()
    deadline = started+180
    with ThreadPoolExecutor(max_workers=4) as workers, (folder/'observations.jsonl').open('x') as raw:
        while pending and time.monotonic()<deadline:
            jobs = {workers.submit(observe,peer,facts):peer for peer in sorted(pending)}
            for job in as_completed(jobs):
                peer = jobs[job]
                try:
                    observation = job.result()
                except (b12.Failure,ValueError,KeyError) as error:
                    observation = dict(peer=peer,utc=utc(),monotonic=time.monotonic(),error=str(error))
                print(json.dumps(observation),file=raw,flush=True)
                if observation.get('exact') and observation['monotonic']<=deadline:
                    found[peer] = observation
                    pending.remove(peer)
                    save(folder/f'as{peer}-observation.json',observation)
            cycle += 3
            while cycle < time.monotonic():
                cycle += 3
            if pending:
                time.sleep(max(0,min(cycle,deadline)-time.monotonic()))
    return found


def verify_block(folder, facts, observations, preflight):
    proofs = {}
    common = None
    signed_body = envelope_body(folder / "tx.signed")
    for peer in PEERS:
        body, encoded, auxiliary, raw, proof = canonical_transaction(
            DB_ROOT / f"as{peer}", observations[peer]["after"], facts["txid"],
            preflight[peer]["block"],
        )
        if encoded != signed_body:
            raise ValueError("Included body differs from signed body")
        if facts["metadata"] is None:
            if auxiliary is not None or 7 in body:
                raise ValueError("Basic ADA trial contains unexpected metadata")
        else:
            value, aux_bytes = auxiliary
            recovered = {str(label): content for label, content in value.value[0].items()}
            if value.tag != 259 or body[7].hex() != digest(aux_bytes) or recovered != facts["metadata"]:
                raise ValueError("Metadata or auxiliary digest mismatch")
        if common is None:
            common = proof
            (folder / "block.cbor").write_bytes(raw)
        if proof != common:
            raise ValueError("Nodes disagree on the containing block")
        proofs[peer] = proof
    save(folder / "block-verification.json", proofs)
    return common


def submit(folder,facts):
    path=f'/tmp/b12-5c-{facts["txid"]}.signed'
    b12.run(['docker','cp',str(folder/'tx.signed'),f'{NODE}:{path}'])
    command=['docker','exec',NODE,'cardano-cli','conway','transaction','submit','--tx-file',path,
             '--testnet-magic',str(MAGIC),'--socket-path','/cardano/node.socket']
    start_utc=utc()
    started=time.monotonic()
    save(folder/'submission-start.json',dict(utc=start_utc,monotonic=started,txid=facts['txid']))
    with (folder/'submit.stdout').open('x') as out, (folder/'submit.stderr').open('x') as err:
        result=subprocess.run(command,stdout=out,stderr=err,timeout=60)
        ended=time.monotonic()
        end_utc=utc()
    response = dict(utc_started=start_utc,utc_response=end_utc,monotonic_started=started,
                    monotonic_response=ended,seconds=ended-started,exit=result.returncode)
    save(folder/'submission-response.json',response)
    result.check_returncode()
    assert b12.parse_txhash((folder/'submit.stdout').read_text())==facts['txid']
    return response


def persist(rows):
    save(ROOT/'trials.json',rows)
    fields=['trial_id','round','position','workload','status','error','txid','input_ref','input_lovelace',
            'payment_ref','payment_lovelace','change_ref','change_lovelace','fee_lovelace','cli_min_fee_lovelace',
            'signed_cbor_bytes','utc_started','utc_response','submission_seconds','block','slot','block_hash',
            'earliest_seconds','spread_seconds','metadata_verified']
    for peer in PEERS:
        fields += [f'as{peer}_utc',f'as{peer}_seconds',f'as{peer}_delay_seconds']
    with (ROOT/'trials.csv.tmp').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    (ROOT/'trials.csv.tmp').replace(ROOT/'trials.csv')


def stats(values):
    if not values:
        return None
    return dict(mean=statistics.mean(values),median=statistics.median(values),min=min(values),max=max(values),
                sample_stdev=statistics.stdev(values) if len(values)>1 else None,
                p95_nearest_rank=sorted(values)[math.ceil(.95*len(values))-1])


def summarize(rows):
    report={}
    for workload in 'ABC':
        group=[row for row in rows if row['workload']==workload]
        success=[row for row in group if row['status']=='VERIFIED']
        metrics=['as150_seconds','earliest_seconds','spread_seconds','submission_seconds',
                 'as151_seconds','as152_seconds','as153_seconds','fee_lovelace','signed_cbor_bytes']
        metrics += [f'as{peer}_delay_seconds' for peer in PEERS]
        not_run=sum(row['status']=='NOT_RUN' for row in group)
        report[workload]=dict(planned=len(group),attempted=len(group)-not_run,success=len(success),
                              failed=len(group)-not_run-len(success),not_run=not_run,
                              statistics={field:stats([float(row[field]) for row in success]) for field in metrics})
    return report


def main():
    if not __debug__:
        raise SystemExit("Run without Python optimization to preserve validation checks")
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    offline = modes.add_parser("summarize")
    offline.add_argument("csv", type=Path)
    modes.add_parser("plan")
    live = modes.add_parser("run")
    live.add_argument("--project", required=True)
    live.add_argument("--output", type=Path, required=True, help="New private output directory")
    live.add_argument("--db-root", type=Path, required=True, help="Parent of the four asNNN DB binds")
    live.add_argument("--keys-root", type=Path, required=True)
    live.add_argument("--cli", type=Path, required=True)
    live.add_argument("--authorize-submit", required=True, choices=PROFILES,
                      help="Explicitly authorize submissions on the selected private network profile")
    args = parser.parse_args()
    if args.mode == "plan":
        print(json.dumps(schedule(), indent=2))
        return 0
    if args.mode == "summarize":
        with args.csv.open(newline="") as file:
            print(json.dumps(summarize(list(csv.DictReader(file))), indent=2))
        return 0

    global ROOT, DB_ROOT, KEYS, CLI, NODES, NODE, RUN_ID, MAGIC
    MAGIC, protocol_major = PROFILES[args.authorize_submit]
    ROOT, DB_ROOT, KEYS, CLI = (path.resolve() for path in
                               (args.output, args.db_root, args.keys_root, args.cli))
    NODES = {}
    for peer in PEERS:
        ids = b12.run(["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={args.project}",
                       "--filter", f"label=com.docker.compose.service=hnode_{peer}_host_0"]).splitlines()
        if len(ids) != 1:
            raise ValueError(f"Expected one running AS{peer} in Compose project")
        NODES[peer] = ids[0]
        mounts = json.loads(b12.run(["docker", "inspect", "--format", "{{json .Mounts}}", ids[0]]))
        if not any(m["Type"] == "bind" and m["Destination"] == "/cardano/db" and
                   Path(m["Source"]).resolve() == DB_ROOT / f"as{peer}" for m in mounts):
            raise ValueError(f"Database bind mismatch for AS{peer}")
    NODE = NODES["150"]
    root_genesis = []
    for node in NODES.values():
        genesis = b12.run(["docker", "exec", node, "cat", "/cardano/shelley-genesis.json"])
        if json.loads(genesis)["networkMagic"] != MAGIC:
            raise ValueError(f"Expected network magic {MAGIC}")
        root_genesis.append(genesis)
    if len(set(root_genesis)) != 1:
        raise ValueError("Node genesis mismatch")
    params = query("150", "protocol-parameters")
    if params["protocolVersion"] != {"major": protocol_major, "minor": 0}:
        raise ValueError(f"Expected {args.authorize_submit} ledger protocol {protocol_major}.0")
    sensor = json.loads((FIXTURES / "sensor.json").read_text())
    if hashlib.sha256((FIXTURES / "measurement.json").read_bytes()).hexdigest() != sensor["1000"]["data_hash"]:
        raise ValueError("Measurement fixture digest mismatch")
    ROOT.mkdir(mode=0o700)
    RUN_ID = os.urandom(8).hex()
    rows = schedule()
    persist(rows)
    tips={peer:query(peer,'tip') for peer in PEERS}
    assert all(tip['era'] == 'Conway' and tip.get('block') is not None
               and tip['syncProgress'] == '100.00' for tip in tips.values())
    assert all(query(peer, 'protocol-parameters') == params for peer in PEERS)
    save(ROOT/'protocol-parameters.json',params)
    sender,recipient=address(1),address(2)
    live=query('150','utxo','--address',sender)
    candidates=[(value['value']['lovelace'],ref) for ref,value in live.items()
                if set(value['value'])=={'lovelace'} and value['address']==sender]
    value,initial=max(candidates)
    assert value>=65_000_000
    magic={}
    versions={}
    for peer in PEERS:
        node=NODES[peer]
        magic[peer]=json.loads(b12.run(['docker','exec',node,'cat','/cardano/shelley-genesis.json']))['networkMagic']
        versions[peer]={tool:b12.run(['docker','exec',node,tool,'--version']) for tool in ('cardano-node','cardano-cli')}
        assert magic[peer] == MAGIC and '11.1.3' in versions[peer]['cardano-node'] and '11.2.3.0' in versions[peer]['cardano-cli']
    save(ROOT/'run-manifest.json',dict(utc=utc(),tips=tips,versions=versions,magic=magic,protocol_version=params["protocolVersion"],sender=sender,
         recipient=recipient,initial_input_ref=initial,sender_utxos=live,
         runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         schedule=rows))
    expected=initial
    used=set()
    ids=set()
    try:
        for row in rows:
            trial=row['trial_id']
            folder=ROOT/'trials'/trial
            folder.mkdir(parents=True)
            row['status']='PREPARATION_FAILED'
            try:
                facts=build(folder,row,expected,sender,recipient,params)
                assert expected not in used and facts['txid'] not in ids
                used.add(expected)
                ids.add(facts['txid'])
                row.update({k:facts[k] for k in ('txid','input_ref','input_lovelace','fee_lovelace',
                                                 'cli_min_fee_lovelace','signed_cbor_bytes')})
                for item in ('payment','change'):
                    row[item+'_ref']=facts[item]['ref']
                    row[item+'_lovelace']=facts[item]['lovelace']
                for peer in PEERS:
                    pre=observe(peer,facts)
                    assert pre['utxos'].get(expected,{}).get('value')=={'lovelace':facts['input_lovelace']}
                    assert all(facts[item]['ref'] not in pre['utxos'] for item in ('payment','change'))
                    save(folder/f'as{peer}-baseline.json',pre)
                preflight={peer:json.loads((folder/f'as{peer}-baseline.json').read_text())['before'] for peer in PEERS}
                row['status']='SUBMISSION_UNRESOLVED'
                persist(rows)
                response=submit(folder,facts)
                row.update(utc_started=response['utc_started'],utc_response=response['utc_response'],
                           submission_seconds=response['seconds'])
                row['status']='INCOMPLETE_OBSERVATION'
                observations=watch(folder,facts,response['monotonic_started'])
                if observations:
                    earliest=min(obs['monotonic'] for obs in observations.values())
                    row['earliest_seconds']=earliest-response['monotonic_started']
                    for peer,obs in observations.items():
                        row[f'as{peer}_utc']=obs['utc']
                        row[f'as{peer}_seconds']=obs['monotonic']-response['monotonic_started']
                        row[f'as{peer}_delay_seconds']=obs['monotonic']-earliest
                assert set(observations)==set(PEERS), f'Missing peers: {set(PEERS)-set(observations)}'
                row['spread_seconds']=max(o['monotonic'] for o in observations.values())-earliest
                row['status']='BLOCK_VERIFICATION_FAILED'
                block=verify_block(folder,facts,observations,preflight)
                row.update({key:block[key] for key in ('block','slot','block_hash')})
                row.update(status='VERIFIED',metadata_verified=True)
                expected=facts['change']['ref']
                print(f"{trial} {row['workload']} verified at block {row['block']} ({row['as150_seconds']:.3f}s AS150)",flush=True)
            except Exception as error:
                row['error']=f'{type(error).__name__}: {error}'
                print(f"{trial}: {row['status']} {row['error']}",file=sys.stderr,flush=True)
                break
            finally:
                persist(rows)
    finally:
        save(ROOT / "summary-statistics.json", summarize(rows))
    return 0 if all(row['status']=='VERIFIED' for row in rows) else 1


if __name__=='__main__':
    sys.exit(main())
