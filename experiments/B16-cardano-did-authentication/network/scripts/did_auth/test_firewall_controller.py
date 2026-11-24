#!/usr/bin/env python3
"""Offline tests for AS183 firewall rule order and partial failures."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1]), *sys.path]):
    import b16_n15_firewall_controller as firewall


class FirewallTests(unittest.TestCase):
    TARGET = "ab" * 32
    NETWORK_ID = "cd" * 32

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="b16-lock-test-")
        self.addCleanup(directory.cleanup)
        self.lock_path = Path(directory.name) / "firewall.lock"
        for patcher in (
            patch.object(firewall, "LOCK_PATH", self.lock_path),
            patch.dict(os.environ, COMPOSE_PROJECT_NAME="b16-test"),
        ):
            self.addCleanup(patcher.stop)
            patcher.start()
        self.metadata = {
            "Id": self.TARGET,
            "Name": "/" + firewall.GATEWAY_CONTAINER,
            "State": {"Running": True},
            "Config": {"Labels": {
                "com.docker.compose.project": "b16-test",
                "com.docker.compose.service": "hnode_183_host_0",
            }},
            "HostConfig": {"NetworkMode": "b16-test_net_183_net0"},
            "NetworkSettings": {"Networks": {
                "b16-test_net_183_net0": {
                    "NetworkID": self.NETWORK_ID, "IPAddress": "10.183.0.71",
                },
            }},
        }
        self.namespace_ip = "10.183.0.71"
        self.chains = {}
        self.unrelated = {}
        for chain in ("INPUT", "OUTPUT"):
            direction = "-s" if chain == "INPUT" else "-d"
            self.unrelated[chain] = (direction, "10.182.0.71", "-j", "ACCEPT")
            self.chains[chain] = [
                self.rule(chain, firewall.ATTACKER_IP, "DROP"),
                self.rule(chain, firewall.CANDIDATE_IP, "DROP"),
                self.unrelated[chain],
            ]
        self.baseline = {chain: rules.copy() for chain, rules in self.chains.items()}
        self.failures = {}
        self.insert_at_end = set()
        self.mutations = []
        patcher = patch.object(firewall.subprocess, "run", side_effect=self.iptables)
        self.addCleanup(patcher.stop)
        patcher.start()

    @staticmethod
    def rule(chain, ip, target):
        direction = "-s" if chain == "INPUT" else "-d"
        return (direction, ip, "-p", "tcp", "--dport", "3001", "-j", target)

    def iptables(self, command, *, check, capture_output, text, timeout):
        self.assertTrue(check and capture_output and text)
        self.assertEqual(timeout, 15)
        if command == ["docker", "inspect", "--type", "container", firewall.GATEWAY_CONTAINER]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps([self.metadata]))
        if command == ["docker", "exec", self.TARGET, "ip", "-o", "-4", "addr", "show", "scope", "global"]:
            return subprocess.CompletedProcess(
                command, 0, stdout=f"2: net0 inet {self.namespace_ip}/24 scope global net0\n"
            )
        self.assertEqual(command[:8], [
            "docker", "exec", "-u", "0", self.TARGET, "iptables", "-w", "5",
        ])
        operation, chain, *spec = command[8:]
        rules = self.chains[chain]
        if operation in ("-I", "-D"):
            self.mutations.append((operation, chain))
        if (operation, chain) in self.failures:
            code, message = self.failures[operation, chain]
            raise CalledProcessError(code, command, stderr=message)
        if operation == "-S":
            lines = ["-P " + chain + " ACCEPT"]
            for direction, ip, *rest in rules:
                if rest[:2] == ["-p", "tcp"]:
                    rest[2:2] = ["-m", "tcp"]
                lines.append(" ".join(["-A", chain, direction, ip + "/32", *rest]))
            return subprocess.CompletedProcess(command, 0, stdout="\n".join(lines))
        elif operation == "-I":
            index = len(rules) if chain in self.insert_at_end else int(spec[0]) - 1
            rules.insert(index, tuple(spec[1:]))
        elif operation == "-D":
            rules.remove(tuple(spec))
        else:
            self.fail(f"Unexpected iptables operation {operation}")
        return subprocess.CompletedProcess(command, 0, stdout="")

    def verdict(self, chain, ip):
        for direction, address, *spec in self.chains[chain]:
            if address == ip:
                return spec[-1]
        return "ACCEPT"

    def test_successful_admission(self):
        firewall.grant()
        for chain in self.chains:
            self.assertEqual(self.verdict(chain, firewall.CANDIDATE_IP), "ACCEPT")
            self.assertEqual(self.verdict(chain, firewall.ATTACKER_IP), "DROP")
            self.assertEqual(self.chains[chain][0], self.baseline[chain][0])
            self.assertEqual(self.chains[chain][2:], self.baseline[chain][1:])

    def test_repeated_admission(self):
        firewall.grant()
        self.mutations.clear()
        with self.assertRaisesRegex(RuntimeError, "AS184_ALREADY_ADMITTED"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_successful_revocation_preserves_unrelated_rules(self):
        firewall.grant()
        for chain, rules in self.chains.items():
            rules.append(self.rule(chain, firewall.CANDIDATE_IP, "ACCEPT"))
        firewall.revoke()
        firewall.revoke()
        self.assertEqual(self.chains, self.baseline)
        for chain in self.chains:
            self.assertEqual(self.verdict(chain, firewall.CANDIDATE_IP), "DROP")
            self.assertEqual(self.verdict(chain, firewall.ATTACKER_IP), "DROP")

    def test_reordered_drop_rules_reject_admission_without_writes(self):
        self.chains["INPUT"][:2] = reversed(self.chains["INPUT"][:2])
        with self.assertRaisesRegex(RuntimeError, "AS183_RULE_ORDER_MISMATCH"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_first_insert_failure(self):
        self.failures["-I", "INPUT"] = (2, "insert failed")
        with self.assertRaises(CalledProcessError):
            firewall.grant()
        self.assertEqual(self.mutations, [("-I", "INPUT")])
        self.assertEqual(self.chains, self.baseline)

    def test_second_insert_failure_rolls_back_input(self):
        self.failures["-I", "OUTPUT"] = (2, "insert failed")
        with self.assertRaises(CalledProcessError):
            firewall.grant()
        self.assertEqual(self.mutations, [("-I", "INPUT"), ("-I", "OUTPUT"), ("-D", "INPUT")])
        self.assertEqual(self.chains, self.baseline)

    def test_ineffective_insert_order_rolls_back_both_chains(self):
        self.insert_at_end.add("OUTPUT")
        with self.assertRaisesRegex(RuntimeError, "AS183_RULE_ORDER_MISMATCH: OUTPUT"):
            firewall.grant()
        self.assertEqual(self.mutations, [
            ("-I", "INPUT"), ("-I", "OUTPUT"), ("-D", "INPUT"), ("-D", "OUTPUT"),
        ])
        self.assertEqual(self.chains, self.baseline)

    def test_rollback_failure_reports_original_and_cleanup_failure(self):
        self.failures["-I", "OUTPUT"] = (2, "insert failed")
        self.failures["-D", "INPUT"] = (2, "delete failed")
        with self.assertRaisesRegex(RuntimeError, r"ROLLBACK_FAILED.*INPUT.*delete failed") as error:
            firewall.grant()
        self.assertIsInstance(error.exception.__cause__, CalledProcessError)
        self.assertEqual(error.exception.__cause__.stderr, "insert failed")
        self.assertEqual(self.verdict("INPUT", firewall.CANDIDATE_IP), "ACCEPT")
        self.assertEqual(self.verdict("OUTPUT", firewall.CANDIDATE_IP), "DROP")

    def test_input_revocation_failure_still_attempts_output(self):
        firewall.grant()
        self.failures["-D", "INPUT"] = (2, "delete failed")
        with self.assertRaisesRegex(RuntimeError, r"REVOCATION_FAILED.*INPUT.*delete failed"):
            firewall.revoke()
        self.assertEqual(self.verdict("INPUT", firewall.CANDIDATE_IP), "ACCEPT")
        self.assertEqual(self.chains["OUTPUT"], self.baseline["OUTPUT"])

    def test_output_revocation_failure_reports_partial_result(self):
        firewall.grant()
        self.failures["-D", "OUTPUT"] = (2, "delete failed")
        with self.assertRaisesRegex(RuntimeError, r"REVOCATION_FAILED.*OUTPUT.*delete failed"):
            firewall.revoke()
        self.assertEqual(self.chains["INPUT"], self.baseline["INPUT"])
        self.assertEqual(self.verdict("OUTPUT", firewall.CANDIDATE_IP), "ACCEPT")

    def test_listing_failure_is_not_treated_as_absence(self):
        firewall.grant()
        self.failures["-S", "INPUT"] = (1, "container unavailable")
        with self.assertRaisesRegex(RuntimeError, r"REVOCATION_FAILED.*INPUT.*container unavailable"):
            firewall.revoke()
        self.assertEqual(self.verdict("INPUT", firewall.CANDIDATE_IP), "ACCEPT")
        self.assertEqual(self.chains["OUTPUT"], self.baseline["OUTPUT"])

    def test_revocation_reports_unverified_deny_order_after_removing_accepts(self):
        firewall.grant()
        self.chains["INPUT"].insert(0, self.chains["INPUT"].pop())
        with self.assertRaisesRegex(RuntimeError, r"REVOCATION_FAILED.*AS183_RULE_ORDER_MISMATCH"):
            firewall.revoke()
        for chain in self.chains:
            self.assertNotIn(self.rule(chain, firewall.CANDIDATE_IP, "ACCEPT"), self.chains[chain])
        self.assertEqual(self.chains["INPUT"][0], self.unrelated["INPUT"])
        self.assertEqual(self.chains["OUTPUT"], self.baseline["OUTPUT"])

    def test_accepts_network_id_mode(self):
        self.metadata["HostConfig"]["NetworkMode"] = self.NETWORK_ID
        firewall.grant()
        self.assertEqual(len(self.mutations), 2)

    def test_rejects_stopped_container(self):
        self.metadata["State"]["Running"] = False
        with self.assertRaisesRegex(RuntimeError, "AS183_CONTAINER_NOT_RUNNING"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_wrong_container_name_or_id(self):
        for attribute, wrong in (("Name", "/other"), ("Id", "short")):
            with self.subTest(attribute=attribute), patch.dict(self.metadata, {attribute: wrong}):
                with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_CONTAINER_IDENTITY"):
                    firewall.revoke()
        self.assertEqual(self.mutations, [])

    def test_rejects_missing_project_or_wrong_service(self):
        labels = self.metadata["Config"]["Labels"]
        for label, value in (("project", None), ("service", "hnode_184_host_0")):
            with self.subTest(label=label), patch.dict(labels, {"com.docker.compose." + label: value}):
                with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_COMPOSE_" + label.upper()):
                    firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_wrong_network_mode(self):
        self.metadata["HostConfig"]["NetworkMode"] = "host"
        with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_NETWORK_MODE"):
            firewall.revoke()
        self.assertEqual(self.mutations, [])

    def test_rejects_wrong_network_attachment(self):
        self.metadata["NetworkSettings"]["Networks"] = {}
        with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_NETWORK"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_missing_network_id(self):
        del self.metadata["NetworkSettings"]["Networks"]["b16-test_net_183_net0"]["NetworkID"]
        with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_NETWORK_ID"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_wrong_inspected_ipv4(self):
        self.metadata["NetworkSettings"]["Networks"]["b16-test_net_183_net0"]["IPAddress"] = "10.184.0.71"
        with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_IPV4_ADDRESS"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_wrong_namespace_ipv4(self):
        self.namespace_ip = "10.184.0.71"
        with self.assertRaisesRegex(RuntimeError, "UNEXPECTED_AS183_NAMESPACE_IPV4_ADDRESS"):
            firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_rejects_replacement_before_first_mutation(self):
        original = firewall.chain_rules

        def replace_after_read(target, chain):
            rules = original(target, chain)
            if chain == "OUTPUT":
                self.metadata["Id"] = "ef" * 32
            return rules

        with patch.object(firewall, "chain_rules", side_effect=replace_after_read):
            with self.assertRaisesRegex(RuntimeError, "AS183_CONTAINER_IDENTITY_CHANGED"):
                firewall.grant()
        self.assertEqual(self.mutations, [])

    def test_lock_rejects_overlapping_grant_and_revoke_then_releases(self):
        with firewall.operation_lock():
            for operation in (firewall.grant, firewall.revoke):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(RuntimeError, "B16_FIREWALL_OPERATION_IN_PROGRESS"):
                        operation()
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.lock_path.stat().st_mode & 0o777, 0o600)
        firewall.grant()
        firewall.revoke()
        self.assertEqual(self.chains, self.baseline)

    def test_rejects_symlink_lock(self):
        self.lock_path.symlink_to(self.lock_path.parent / "other")
        with self.assertRaises(OSError):
            firewall.grant()
        self.assertEqual(self.mutations, [])


if __name__ == "__main__":
    unittest.main()
