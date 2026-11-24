"""Disposable fixtures for B16 offline security tests."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import create_authority
import enrollment
import identity
from prototype import did_from_public_key, public_bytes


class EnrollmentFixture(unittest.TestCase):
    NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)
    NODE = "AS184"
    IP = "10.184.0.71"
    NONCE = "12" * 32

    def use_patch(self, patcher):
        self.addCleanup(patcher.stop)
        return patcher.start()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="b16-security-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        public = self.root / "identity-data/public"
        certificates = self.root / "identity-data/enrollments"
        private = self.root / "authority/administrator.pem"
        anchor = self.root / "identity-data/trust/administrator-public.pem"

        for module, name, value in (
            (identity, "PRIVATE_DIR", self.root / "identity-data/keys"),
            (identity, "PUBLIC_DIR", public),
            (enrollment, "PUBLIC_DIR", public),
            (enrollment, "ENROLLMENT_DIR", certificates),
            (enrollment, "ADMIN_KEY", private),
            (enrollment, "TRUSTED_KEY", anchor),
            (create_authority, "PRIVATE_DIR", private.parent),
            (create_authority, "PRIVATE_FILE", private),
            (create_authority, "PUBLIC_FILE", anchor),
        ):
            self.use_patch(patch.object(module, name, value))
        self.use_patch(patch.object(enrollment, "utc_now", return_value=self.NOW))
        self.use_patch(patch("getpass.getpass", return_value="synthetic-fixture-passphrase"))
        with patch("builtins.print"):
            self.create_enrollment()

        self.record_path = public / "AS184.json"
        self.certificate_path = certificates / "AS184-enrollment.json"
        self.anchor = anchor

    def create_enrollment(self):

        self.record = identity.create_identity(self.NODE)
        self.did = self.record["did"]
        self.key = identity.load_private_key(self.NODE)
        identity.create_identity("AS185")
        self.other_key = identity.load_private_key("AS185")
        self.other_did = did_from_public_key(public_bytes(self.other_key))
        create_authority.main()
        enrollment.issue()
