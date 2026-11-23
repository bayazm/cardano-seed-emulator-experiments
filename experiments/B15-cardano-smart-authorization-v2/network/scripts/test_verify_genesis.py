"""Offline tests for the optional B15 genesis freshness check."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import verify_genesis


class GenesisFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        clock = patch.object(verify_genesis, "datetime")
        self.addCleanup(clock.stop)
        self.clock = clock.start()
        self.clock.now.return_value = self.now

    def test_future_start_is_accepted(self):
        verify_genesis.verify_start(
            self.now + timedelta(seconds=1), require_future_start=True,
        )
        self.clock.now.assert_called_once_with(timezone.utc)

    def test_past_or_current_start_is_rejected_in_fresh_mode(self):
        for start in (self.now - timedelta(seconds=1), self.now):
            with self.subTest(start=start):
                with self.assertRaisesRegex(ValueError, "later than the current UTC time"):
                    verify_genesis.verify_start(start, require_future_start=True)

    def test_past_start_is_accepted_without_fresh_mode(self):
        verify_genesis.verify_start(
            self.now - timedelta(seconds=1), require_future_start=False,
        )
        self.clock.now.assert_not_called()
