"""Offline tests for the B15 controller and both operator entry points."""

import argparse
import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import admission_controller as registry
import enforce_admission
import enforce_revocation
import registry_firewall as firewall

ADDRESS = "addr_test_registry_fixture"
POLICY = "a" * 56
REFERENCE = "b" * 64 + "#0"
OTHER_REFERENCE = "c" * 64 + "#1"
PROJECT = "b15-mock"
NETWORK = f"{PROJECT}_net_183_net0"
CONTAINER_ID = "d" * 64


def registry_outputs(revision=1, authorized=True):
    return {
        REFERENCE: {
            "address": ADDRESS,
            "value": {"lovelace": 5000000, POLICY: {registry.TOKEN_NAME: 1}},
            "inlineDatum": {
                "constructor": 0,
                "fields": [
                    {"bytes": registry.EXPECTED_NODE.encode().hex()},
                    {"bytes": registry.EXPECTED_IP.encode().hex()},
                    {"constructor": int(authorized), "fields": []},
                    {"int": revision},
                ],
            },
        },
    }


def listed_rule(rule):
    chain, direction, ip, protocol_option, protocol, *rest = rule
    return (chain, direction, ip + "/32", protocol_option, protocol, "-m", "tcp", *rest)


class MockFirewall:
    def __init__(self):
        self.unrelated = {
            chain: [(chain, "-j", "ACCEPT"), (chain, "-j", "LOG")]
            for chain in ("INPUT", "OUTPUT")
        }
        self.entries = deepcopy(self.unrelated)
        self.drops = {rule[0]: listed_rule(rule) for rule in firewall.RULES}
        self.failures = set()
        self.mutations = []
        self.rule_commands = []
        self.ip = firewall.AS183_IP
        self.container = {
            "Id": CONTAINER_ID,
            "Name": "/" + registry.AUTHORIZED_NODES["AS183"],
            "State": {"Running": True},
            "Config": {"Labels": {
                "com.docker.compose.project": PROJECT,
                "com.docker.compose.service": "hnode_183_host_0",
            }},
            "HostConfig": {"NetworkMode": NETWORK},
            "NetworkSettings": {"Networks": {
                NETWORK: {"IPAddress": firewall.AS183_IP, "NetworkID": "e" * 64},
            }},
        }

    def run(self, command, *, check, **kwargs):
        assert check
        if command == ["docker", "inspect", "--type", "container", registry.AUTHORIZED_NODES["AS183"]]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps([self.container]))
        if command == ["docker", "exec", CONTAINER_ID, "ip", "-o", "-4", "addr", "show", "scope", "global"]:
            return subprocess.CompletedProcess(command, 0, stdout=f"2: eth0 inet {self.ip}/24 scope global eth0")
        assert command[:5] == ["docker", "exec", CONTAINER_ID, "iptables", "-w"]
        self.rule_commands.append(command)
        action, chain, *spec = command[5:]
        entries = self.entries[chain]
        if (action, chain) in self.failures:
            raise subprocess.CalledProcessError(1, command, stderr="fixture failure")
        if action == "-S":
            stdout = f"-P {chain} ACCEPT\n"
            stdout += "".join("-A " + " ".join(entry) + "\n" for entry in entries)
            return subprocess.CompletedProcess(command, 0, stdout=stdout)
        self.mutations.append((action, chain))
        if action == "-I":
            assert spec[0] == "1"
            entries.insert(0, listed_rule((chain, *spec[1:])))
        elif action == "-D":
            entries.remove((chain, *spec))
        else:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    def block(self, chain):
        self.entries[chain].insert(0, self.drops[chain])


class EnforcementTests(unittest.TestCase):
    def setUp(self):
        self.fw = MockFirewall()
        lock_dir = TemporaryDirectory()
        self.addCleanup(lock_dir.cleanup)
        self.stack_patch(
            firewall, "LOCK_PATH", new=Path(lock_dir.name) / "b15-firewall.lock",
        )
        environment = patch.dict(firewall.os.environ, {"COMPOSE_PROJECT_NAME": PROJECT})
        environment.start()
        self.addCleanup(environment.stop)
        self.stack_patch(registry, "registry_parameters", return_value=(ADDRESS, POLICY))
        self.query = self.stack_patch(registry, "query_registry")
        self.stack_patch(firewall.subprocess, "run", side_effect=self.fw.run)
        self.args = argparse.Namespace(apply=True)
        self.stack_patch(argparse.ArgumentParser, "parse_args", return_value=self.args)

    def stack_patch(self, target, name, **kwargs):
        patcher = patch.object(target, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def run_main(self, module):
        with redirect_stdout(io.StringIO()) as output:
            module.main()
        return output.getvalue()

    def assert_blocked(self):
        for chain, entries in self.fw.entries.items():
            self.assertEqual(entries[0], self.fw.drops[chain])

    def test_controller_dry_run_authorizes(self):
        self.query.return_value = registry_outputs()
        output = self.run_main(registry)
        decision = json.loads(output.split("AUTHORIZATION VERIFICATION PASSED")[1])
        self.assertEqual(decision["decision"], "ALLOW")
        self.assertEqual(decision["verified_nodes"], list(registry.AUTHORIZED_NODES))
        self.assertEqual(self.query.call_count, 4)
        self.assertFalse(self.fw.mutations)

    def test_valid_and_repeated_admission(self):
        self.query.return_value = registry_outputs()
        self.fw.block("INPUT")
        self.fw.block("INPUT")
        self.fw.block("OUTPUT")
        self.assertIn('"rules_removed": 3', self.run_main(enforce_admission))
        self.assertIn('"firewall_modified": false', self.run_main(enforce_admission))
        self.assertEqual(self.fw.entries, self.fw.unrelated)
        self.assertEqual(self.query.call_count, 16)

    def test_valid_and_repeated_revocation_with_shadowed_drop(self):
        self.query.return_value = registry_outputs(2, False)
        self.fw.entries["INPUT"].append(self.fw.drops["INPUT"])
        self.assertIn('"rules_added": 2', self.run_main(enforce_revocation))
        self.assertIn('"firewall_modified": false', self.run_main(enforce_revocation))
        self.assert_blocked()
        for chain, entries in self.fw.entries.items():
            self.assertEqual(
                [entry for entry in entries if entry != self.fw.drops[chain]],
                self.fw.unrelated[chain],
            )

    def test_disagreement_by_reference_or_datum(self):
        for different in (
            {OTHER_REFERENCE: registry_outputs()[REFERENCE]},
            registry_outputs(2, False),
        ):
            with self.subTest(different=different):
                self.query.side_effect = [registry_outputs()] * 3 + [different]
                with self.assertRaisesRegex(ValueError, "disagree"):
                    self.run_main(enforce_admission)
        self.assertFalse(self.fw.mutations)

    def test_missing_or_ambiguous_registry(self):
        outputs = registry_outputs()
        outputs[OTHER_REFERENCE] = outputs[REFERENCE]
        for data in ({}, outputs):
            with self.subTest(count=len(data)):
                self.query.return_value = data
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    self.run_main(enforce_admission)
        self.assertFalse(self.fw.mutations)

    def test_wrong_policy_name_quantity_or_address(self):
        for values, address, message in (
            ({"d" * 56: {registry.TOKEN_NAME: 1}}, ADDRESS, "exactly one"),
            ({POLICY: {"00": 1}}, ADDRESS, "exactly one"),
            ({POLICY: {registry.TOKEN_NAME: 2}}, ADDRESS, "quantity"),
            ({POLICY: {registry.TOKEN_NAME: True}}, ADDRESS, "quantity"),
            ({POLICY: {registry.TOKEN_NAME: 1}}, "different", "address"),
        ):
            with self.subTest(values=values, address=address):
                output = registry_outputs()[REFERENCE]
                output.update(value=values, address=address)
                with self.assertRaisesRegex(ValueError, message):
                    registry.find_registry({REFERENCE: output}, ADDRESS, POLICY)

    def test_wrong_revision_or_authorization(self):
        for args, message in (((3, True), "revision"), ((1, False), "authorization")):
            with self.subTest(args=args):
                self.query.return_value = registry_outputs(*args)
                with self.assertRaisesRegex(ValueError, message):
                    self.run_main(enforce_admission)
        self.assertFalse(self.fw.mutations)

    def test_reference_changes_between_checks(self):
        for module, data in (
            (enforce_admission, registry_outputs()),
            (enforce_revocation, registry_outputs(2, False)),
        ):
            with self.subTest(module=module.__name__):
                self.query.side_effect = [data] * 4 + [
                    {OTHER_REFERENCE: data[REFERENCE]},
                ] * 4
                with self.assertRaisesRegex(RuntimeError, "Registry changed"):
                    self.run_main(module)
        self.assertFalse(self.fw.mutations)

    def test_state_changes_between_checks(self):
        self.query.side_effect = [registry_outputs()] * 4 + [registry_outputs(2, False)] * 4
        with self.assertRaisesRegex(ValueError, "revision"):
            self.run_main(enforce_admission)
        self.assertFalse(self.fw.mutations)

    def test_partial_admission_closes_both_directions_and_can_retry(self):
        self.query.return_value = registry_outputs()
        self.fw.block("INPUT")
        self.fw.block("OUTPUT")
        self.fw.failures.add(("-D", "OUTPUT"))
        with self.assertRaisesRegex(RuntimeError, "DROPs restored"):
            self.run_main(enforce_admission)
        self.assert_blocked()
        self.fw.failures.clear()
        self.run_main(enforce_admission)
        self.assertEqual(self.fw.entries, self.fw.unrelated)

    def test_admission_repairs_a_preexisting_partial_state(self):
        self.query.return_value = registry_outputs()
        self.fw.block("OUTPUT")
        self.assertIn('"rules_removed": 1', self.run_main(enforce_admission))
        self.assertEqual(self.fw.entries, self.fw.unrelated)

    def test_admission_reports_incomplete_recovery(self):
        self.query.return_value = registry_outputs()
        self.fw.block("INPUT")
        self.fw.block("OUTPUT")
        self.fw.failures.update({("-D", "OUTPUT"), ("-I", "INPUT")})
        with self.assertRaisesRegex(RuntimeError, "recovery incomplete.*INPUT"):
            self.run_main(enforce_admission)

    def test_partial_revocation_retains_drop_and_can_retry(self):
        self.query.return_value = registry_outputs(2, False)
        self.fw.failures.add(("-I", "INPUT"))
        with self.assertRaisesRegex(RuntimeError, "INPUT has no leading"):
            self.run_main(enforce_revocation)
        self.assertEqual(self.fw.entries["OUTPUT"][0], self.fw.drops["OUTPUT"])
        self.assertEqual(self.fw.entries["INPUT"], self.fw.unrelated["INPUT"])
        self.fw.failures.clear()
        self.assertIn('"rules_added": 1', self.run_main(enforce_revocation))
        self.assert_blocked()

    def test_listing_failure_is_reported(self):
        self.query.return_value = registry_outputs(2, False)
        self.fw.failures.add(("-S", "OUTPUT"))
        with self.assertRaisesRegex(RuntimeError, "OUTPUT verification"):
            self.run_main(enforce_revocation)
        self.assertEqual(self.fw.entries["INPUT"][0], self.fw.drops["INPUT"])

    def assert_target_rejected(self, pattern):
        for module, outputs in (
            (enforce_admission, registry_outputs()),
            (enforce_revocation, registry_outputs(2, False)),
        ):
            with self.subTest(module=module.__name__):
                self.query.return_value = outputs
                with self.assertRaisesRegex(RuntimeError, pattern):
                    self.run_main(module)
        self.assertFalse(self.fw.rule_commands)

    def test_rejects_wrong_compose_project(self):
        self.fw.container["Config"]["Labels"]["com.docker.compose.project"] = "other"
        self.assert_target_rejected("Compose project")

    def test_rejects_wrong_compose_service(self):
        self.fw.container["Config"]["Labels"]["com.docker.compose.service"] = "hnode_182_host_0"
        self.assert_target_rejected("Compose service")

    def test_rejects_wrong_container_identity(self):
        self.fw.container["Name"] = "/unexpected"
        self.assert_target_rejected("container identity")

    def test_rejects_wrong_as183_ip(self):
        self.fw.ip = "10.183.0.72"
        self.assert_target_rejected("IPv4 address in its network namespace")

    def test_rejects_wrong_docker_network_ip(self):
        self.fw.container["NetworkSettings"]["Networks"][NETWORK]["IPAddress"] = "10.183.0.72"
        self.assert_target_rejected("IPv4 address")

    def test_rejects_stopped_container(self):
        self.fw.container["State"]["Running"] = False
        self.assert_target_rejected("stopped")

    def test_rejects_unexpected_network_namespace(self):
        for mode in ("host", "container:other", "none", "bridge"):
            with self.subTest(mode=mode):
                self.fw.container["HostConfig"]["NetworkMode"] = mode
                self.assert_target_rejected("network namespace")

    def test_admission_and_revocation_cannot_overlap(self):
        def assert_revocation_locked():
            queries = self.query.call_count
            commands = len(self.fw.rule_commands)
            with self.assertRaisesRegex(RuntimeError, "holds the lock"):
                enforce_revocation.main()
            self.assertEqual(self.query.call_count, queries)
            self.assertEqual(len(self.fw.rule_commands), commands)

        def query_during_admission(*args):
            assert_revocation_locked()
            return registry_outputs()

        def command_during_admission(command, **kwargs):
            if command[3:6] == ["iptables", "-w", "-S"]:
                assert_revocation_locked()
            return self.fw.run(command, **kwargs)

        self.query.side_effect = query_during_admission
        self.stack_patch(firewall.subprocess, "run", side_effect=command_during_admission)
        self.fw.block("INPUT")
        self.fw.block("OUTPUT")
        self.run_main(enforce_admission)
        self.assertEqual(self.fw.entries, self.fw.unrelated)

    def test_failed_admission_releases_lock_for_revocation(self):
        self.query.return_value = registry_outputs()
        self.fw.block("INPUT")
        self.fw.block("OUTPUT")
        self.fw.failures.add(("-D", "OUTPUT"))
        with self.assertRaisesRegex(RuntimeError, "DROPs restored"):
            self.run_main(enforce_admission)
        self.query.return_value = registry_outputs(2, False)
        self.assertIn('"firewall_modified": false', self.run_main(enforce_revocation))
        self.assert_blocked()

    def test_rejects_container_replacement_before_rule_change(self):
        def replace_after_listing(command, **kwargs):
            result = self.fw.run(command, **kwargs)
            if command[-2:] == ["-S", "INPUT"]:
                self.fw.container["Id"] = "f" * 64
            return result

        self.query.return_value = registry_outputs()
        self.fw.block("INPUT")
        self.stack_patch(firewall.subprocess, "run", side_effect=replace_after_listing)
        with self.assertRaisesRegex(RuntimeError, "container identity changed"):
            self.run_main(enforce_admission)
        self.assertFalse(self.fw.mutations)

    def test_preserves_similar_but_unrelated_rules(self):
        self.query.return_value = registry_outputs()
        for chain, rule in self.fw.drops.items():
            self.fw.entries[chain].append((*rule[:-2], "-m", "comment", "--comment", "operator", *rule[-2:]))
            self.fw.unrelated[chain] = self.fw.entries[chain][:]
            self.fw.block(chain)
        self.run_main(enforce_admission)
        self.assertEqual(self.fw.entries, self.fw.unrelated)
        self.query.return_value = registry_outputs(2, False)
        self.run_main(enforce_revocation)
        for chain, entries in self.fw.entries.items():
            self.assertEqual(entries, [self.fw.drops[chain], *self.fw.unrelated[chain]])

    def test_enforcement_dry_runs_never_write_rules(self):
        self.args.apply = False
        self.query.return_value = registry_outputs()
        self.assertIn("DRY RUN", self.run_main(enforce_admission))
        self.query.return_value = registry_outputs(2, False)
        self.assertIn("DRY RUN", self.run_main(enforce_revocation))
        self.assertFalse(self.fw.mutations)


if __name__ == "__main__":
    unittest.main()
