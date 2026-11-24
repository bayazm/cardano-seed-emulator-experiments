#!/usr/bin/env python3
"""Exercise B16 enrollment and Ed25519 proof of possession offline."""

import json
import unittest
from datetime import timedelta
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization

import enrollment
import prototype
from security_fixtures import EnrollmentFixture


class IdentityTests(EnrollmentFixture):
    def setUp(self):
        super().setUp()
        self.certificate = json.loads(self.certificate_path.read_text())
        self.gateway = prototype.AdmissionGateway({self.NODE: self.did})
        self.clock = self.use_patch(patch.object(prototype.time, "monotonic", return_value=10))
        self.nonces = self.use_patch(patch.object(
            prototype.secrets, "token_hex", side_effect=[self.NONCE, "34" * 32]
        ))

    def verify_certificate(self, **overrides):
        expected = dict(expected_node=self.NODE, expected_ip=self.IP, expected_did=self.did)
        return enrollment.verify_certificate(self.certificate, **{**expected, **overrides})

    def challenge(self, node=None, did=None):
        return self.gateway.issue_challenge(node or self.NODE, did or self.did)

    def sign(self, nonce, key=None, gateway=prototype.GATEWAY, did=None):
        return (key or self.key).sign(
            prototype.signed_message(self.NODE, did or self.did, gateway, nonce)
        )

    def verify(self, nonce, signature, node=None, did=None):
        return self.gateway.verify(
            node or self.NODE, did or self.did, prototype.GATEWAY, nonce, signature
        )

    def test_valid_enrollment(self):
        self.assertEqual(self.certificate["payload"]["schema"], "B16-DID-ENROLLMENT-v1")
        self.assertEqual(self.certificate["payload"]["network"], "B16-cardano-5556")
        self.assertTrue(self.verify_certificate())

    def test_valid_proof_of_possession(self):
        nonce = self.challenge()
        self.nonces.assert_called_once_with(32)
        self.assertEqual(self.verify(nonce, self.sign(nonce)), (True, "IDENTITY_AUTHENTICATED"))

    def test_invalid_signature_consumes_challenge(self):
        nonce = self.challenge()
        signature = self.sign(nonce)
        corrupt = bytes([signature[0] ^ 1]) + signature[1:]
        self.assertEqual(self.verify(nonce, corrupt), (False, "INVALID_SIGNATURE_OR_DID"))
        self.assertEqual(self.verify(nonce, signature), (False, "UNKNOWN_OR_REPLAYED_CHALLENGE"))

    def test_wrong_private_key(self):
        nonce = self.challenge()
        self.assertEqual(
            self.verify(nonce, self.sign(nonce, self.other_key)), (False, "INVALID_SIGNATURE_OR_DID")
        )

    def test_unknown_did(self):
        nonce = self.challenge(did=self.other_did)
        signature = self.sign(nonce, self.other_key, did=self.other_did)
        self.assertEqual(
            self.verify(nonce, signature, did=self.other_did), (False, "DID_NOT_ENROLLED_FOR_NODE")
        )

    def test_did_substitution(self):
        with self.assertRaisesRegex(ValueError, "Enrollment identity mismatch"):
            self.verify_certificate(expected_did=self.other_did)

    def test_wrong_trust_anchor(self):
        self.anchor.write_bytes(self.other_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        with self.assertRaisesRegex(ValueError, "Invalid administrator signature"):
            self.verify_certificate()

    def test_altered_nonce_in_signed_message(self):
        nonce = self.challenge()
        self.assertEqual(
            self.verify(nonce, self.sign("56" * 32)), (False, "INVALID_SIGNATURE_OR_DID")
        )

    def test_consumed_challenge_reuse(self):
        nonce = self.challenge()
        signature = self.sign(nonce)
        self.assertTrue(self.verify(nonce, signature)[0])
        self.assertEqual(self.verify(nonce, signature), (False, "UNKNOWN_OR_REPLAYED_CHALLENGE"))

    def test_old_signature_for_fresh_challenge(self):
        first = self.challenge()
        signature = self.sign(first)
        self.assertTrue(self.verify(first, signature)[0])
        second = self.challenge()
        self.assertNotEqual(first, second)
        self.assertEqual(self.verify(second, signature), (False, "INVALID_SIGNATURE_OR_DID"))

    def test_challenge_expiry(self):
        nonce = self.challenge()
        self.clock.return_value = 41
        self.assertEqual(self.verify(nonce, self.sign(nonce)), (False, "EXPIRED_CHALLENGE"))

    def test_enrollment_expiry(self):
        with self.assertRaisesRegex(ValueError, "Certificate expired"):
            self.verify_certificate(now=self.NOW + timedelta(days=30))

    def test_wrong_gateway_identity(self):
        nonce = self.challenge()
        self.assertEqual(
            self.verify(nonce, self.sign(nonce, gateway="AS999")), (False, "INVALID_SIGNATURE_OR_DID")
        )

    def test_wrong_candidate_node(self):
        with self.assertRaisesRegex(ValueError, "Enrollment identity mismatch"):
            self.verify_certificate(expected_node="AS185")
        nonce = self.challenge()
        self.assertEqual(
            self.verify(nonce, self.sign(nonce), node="AS185"), (False, "CHALLENGE_CONTEXT_MISMATCH")
        )

    def test_wrong_candidate_ip(self):
        with self.assertRaisesRegex(ValueError, "Enrollment identity mismatch"):
            self.verify_certificate(expected_ip="10.185.0.71")

    def test_signed_candidate_ip_cannot_be_altered(self):
        self.certificate["payload"]["ip"] = "10.185.0.71"
        with self.assertRaisesRegex(ValueError, "Invalid administrator signature"):
            self.verify_certificate(expected_ip="10.185.0.71")


if __name__ == "__main__":
    unittest.main()
