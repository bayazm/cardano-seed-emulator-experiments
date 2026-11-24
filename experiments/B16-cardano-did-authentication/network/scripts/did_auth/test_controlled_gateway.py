#!/usr/bin/env python3
"""Run the controlled gateway with synthetic identities and mocked I/O."""

import copy
import importlib
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import prototype
from security_fixtures import EnrollmentFixture

SCRIPTS = Path(__file__).resolve().parents[1]
ADDRESS = "synthetic-membership-address"
POLICY = "ab" * 28
TOKEN = b"B15_REGISTRY".hex()
REFERENCE = "ab" * 32 + "#0"


def registry_output(node="AS184", ip="10.184.0.71", authorized=True, revision=1):
    return {
        REFERENCE: {
            "address": ADDRESS,
            "value": {POLICY: {TOKEN: 1}},
            "inlineDatum": {
                "constructor": 0,
                "fields": [
                    {"bytes": node.encode().hex()},
                    {"bytes": ip.encode().hex()},
                    {"constructor": int(authorized), "fields": []},
                    {"int": revision},
                ],
            },
        },
    }


class GatewayTests(EnrollmentFixture):
    @classmethod
    def setUpClass(cls):
        def binding(path):
            return {"membership-script.addr": ADDRESS, "policy-id.txt": POLICY}[path.name]

        with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
            with patch.object(Path, "read_text", binding):
                cls.gateway = importlib.import_module("b16_n15_controlled_gateway")
                cls.registry = importlib.import_module("b16_integrated_admission")
                cls.firewall = importlib.import_module("b16_n15_firewall_controller")

    def setUp(self):
        super().setUp()
        self.use_patch(patch.object(self.gateway, "ROOT", self.root))
        self.use_patch(patch.object(self.registry, "REGISTRY_ADDR", ADDRESS))
        self.use_patch(patch.object(self.registry, "POLICY_ID", POLICY))
        self.use_patch(patch.object(prototype.secrets, "token_hex", return_value=self.NONCE))
        self.use_patch(patch.object(prototype.time, "monotonic", return_value=10))
        self.query = self.use_patch(patch.object(
            self.registry, "query_registry", return_value=registry_output()
        ))
        self.grant = self.use_patch(patch.object(self.gateway, "grant"))
        socket = self.use_patch(patch.object(self.gateway.socket, "socket"))
        self.server = socket.return_value.__enter__.return_value
        self.connection = socket.return_value
        self.server.accept.return_value = (self.connection, (self.IP, 12345))
        self.stream = self.connection.makefile.return_value.__enter__.return_value
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        for redirect in (redirect_stdout, redirect_stderr):
            context = redirect(self.output)
            context.__enter__()
            self.addCleanup(context.__exit__, None, None, None)

    def run_gateway(self, *, key=None, source=None, node=None, did=None):
        if source:
            self.server.accept.return_value = (self.connection, (source, 12345))
        signature = (key or self.key).sign(
            prototype.signed_message(self.NODE, self.did, prototype.GATEWAY, self.NONCE)
        )
        request = {"node": node or self.NODE, "did": did or self.did}
        response = {"type": "RESPONSE", "signature": signature.hex()}
        wire = io.BytesIO(b"".join(json.dumps(message).encode() + b"\n"
                                   for message in (request, response)))
        self.stream.readline.side_effect = wire.readline
        self.gateway.main()
        return json.loads(self.stream.write.call_args.args[0])

    def assert_denied(self, reason):
        result = self.run_gateway()
        self.assertEqual(result["authorization_reason"], reason)
        self.assertEqual(result["decision"], "DENY")
        self.assertIs(result["authenticated"], True)
        self.assertEqual(result["network_admission"], "NOT_GRANTED")
        self.grant.assert_not_called()

    def test_all_gates_allow_firewall_grant(self):
        result = self.run_gateway()
        self.assertIs(result["authenticated"], True)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["network_admission"], "GRANTED")
        self.assertEqual(self.query.call_count, 4)
        self.grant.assert_called_once_with()

    def test_unauthorized_registry(self):
        self.query.return_value = registry_output(authorized=False, revision=0)
        self.assert_denied("CARDANO_AUTHORIZATION_REVOKED")

    def test_authorized_registry_with_wrong_key(self):
        result = self.run_gateway(key=self.other_key)
        self.assertIs(result["authenticated"], False)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["network_admission"], "NOT_GRANTED")
        self.query.assert_not_called()
        self.grant.assert_not_called()

    def test_invalid_enrollment(self):
        certificate = json.loads(self.certificate_path.read_text())
        serial = certificate["payload"]["serial"]
        certificate["payload"]["serial"] = ("1" if serial[0] == "0" else "0") + serial[1:]
        self.certificate_path.write_text(json.dumps(certificate))
        with self.assertRaisesRegex(ValueError, "Invalid administrator signature"):
            self.run_gateway()
        self.server.accept.assert_not_called()
        self.query.assert_not_called()
        self.grant.assert_not_called()

    def test_public_key_substitution(self):
        self.record["public_key_hex"] = prototype.public_bytes(self.other_key).hex()
        self.record_path.write_text(json.dumps(self.record))
        with self.assertRaisesRegex(ValueError, "DID_PUBLIC_KEY_MISMATCH"):
            self.run_gateway()
        self.query.assert_not_called()
        self.grant.assert_not_called()

    def test_registry_disagreement(self):
        self.query.side_effect = [registry_output()] * 3 + [registry_output(revision=3)]
        self.assert_denied("REGISTRY_VERIFICATION_FAILED")
        self.assertIn("REGISTRY_CONSENSUS_MISMATCH", self.output.getvalue())

    def test_missing_registry_nft(self):
        self.query.return_value[REFERENCE]["value"] = {"lovelace": 5000000}
        self.assert_denied("REGISTRY_VERIFICATION_FAILED")
        self.assertIn("REGISTRY_NFT_NOT_UNIQUE", self.output.getvalue())

    def test_ambiguous_registry_nft(self):
        utxos = self.query.return_value
        utxos["cd" * 32 + "#0"] = copy.deepcopy(utxos[REFERENCE])
        self.assert_denied("REGISTRY_VERIFICATION_FAILED")
        self.assertIn("REGISTRY_NFT_NOT_UNIQUE", self.output.getvalue())

    def test_registry_node_mismatch(self):
        self.query.return_value = registry_output(node="AS185")
        self.assert_denied("REGISTRY_NODE_MISMATCH")

    def test_registry_ip_mismatch(self):
        self.query.return_value = registry_output(ip="10.185.0.71")
        self.assert_denied("REGISTRY_IP_MISMATCH")

    def test_revoked_registry(self):
        self.query.return_value = registry_output(authorized=False, revision=2)
        self.assert_denied("CARDANO_AUTHORIZATION_REVOKED")

    def test_repeated_admission_does_not_write_rules(self):
        self.grant.side_effect = self.firewall.grant
        self.use_patch(patch.object(self.firewall, "LOCK_PATH", self.root / "firewall.lock"))
        target = "ab" * 32
        self.use_patch(patch.object(self.firewall, "validate_target", return_value=target))
        iptables = self.use_patch(patch.object(self.firewall, "iptables", return_value=(
            "-A INPUT -s 10.184.0.71/32 -p tcp -m tcp --dport 3001 -j ACCEPT\n"
        )))
        result = self.run_gateway()
        self.assertIs(result["authenticated"], True)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["network_admission"], "NOT_GRANTED")
        self.assertEqual(result["authorization_reason"], "FIREWALL_ENFORCEMENT_FAILED")
        self.assertIn("AS184_ALREADY_ADMITTED", self.output.getvalue())
        self.assertTrue(iptables.called)
        iptables.assert_called_once_with(target, "-S", "INPUT")

    def test_incomplete_rollback_reports_unknown_firewall_state(self):
        self.grant.side_effect = self.firewall.FirewallRollbackError("synthetic rollback failure")
        result = self.run_gateway()
        self.assertIs(result["authenticated"], True)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["network_admission"], "NOT_GRANTED")
        self.assertIn('"firewall_modified": null', self.output.getvalue())

    def test_unexpected_tcp_source_address(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_SOURCE_IP"):
            self.run_gateway(source="10.186.0.71")
        self.stream.readline.assert_not_called()
        self.query.assert_not_called()
        self.grant.assert_not_called()

    def test_as185_attempts_admission(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_SOURCE_IP"):
            self.run_gateway(source="10.185.0.71", node="AS185",
                             did=self.other_did, key=self.other_key)
        self.stream.write.assert_not_called()
        self.query.assert_not_called()
        self.grant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
