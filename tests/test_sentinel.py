import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytz


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_sentinel():
    os.environ["HONEYCOMB_API_KEY"] = "test-key"
    if "sentinel" in sys.modules:
        return importlib.reload(sys.modules["sentinel"])
    return importlib.import_module("sentinel")


class FixedDateTime:
    fixed_now = None

    @classmethod
    def now(cls, tz=None):
        return cls.fixed_now


class SentinelTests(unittest.TestCase):
    def setUp(self) -> None:
        for key in (
            "SENTINEL_GOD_MODE",
            "SENTINEL_GOD_MODE_TOKEN",
            "SENTINEL_GOD_MODE_SECRET",
        ):
            os.environ.pop(key, None)
        self.sentinel = load_sentinel()

    def test_legacy_god_mode_env_is_rejected(self) -> None:
        os.environ["SENTINEL_GOD_MODE"] = "true"
        with patch.object(self.sentinel, "_write_audit_event") as audit_mock:
            result = self.sentinel.check_god_mode()

        self.assertFalse(result["active"])
        self.assertEqual(result["reason"], "legacy_env_override_retired")
        audit_mock.assert_called_once()

    def test_valid_signed_god_mode_token_returns_operator_metadata(self) -> None:
        os.environ["SENTINEL_GOD_MODE_TOKEN"] = "signed-token"
        os.environ["SENTINEL_GOD_MODE_SECRET"] = "shared-secret"

        with patch.object(
            self.sentinel,
            "validate_god_mode_token",
            return_value=("zoagrad", 3, 1_744_992_000),
        ), patch.object(self.sentinel, "_write_audit_event") as audit_mock:
            result = self.sentinel.check_god_mode()

        self.assertTrue(result["active"])
        self.assertEqual(result["operator"], "zoagrad")
        self.assertEqual(result["locked_hour"], 3)
        expected_expiry = datetime.fromtimestamp(1_744_992_000, tz=timezone.utc).isoformat()
        self.assertEqual(result["expires_utc"], expected_expiry)
        audit_mock.assert_called_once()

    def test_assess_human_cost_writes_local_status_snapshot(self) -> None:
        denver = pytz.timezone("America/Denver")
        fixed_now = denver.localize(datetime(2026, 4, 18, 13, 30, 0))
        FixedDateTime.fixed_now = fixed_now

        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "sentinel_status.json"
            with patch.object(self.sentinel, "STATUS_PATH", status_path), patch.object(
                self.sentinel, "datetime", FixedDateTime
            ), patch.object(
                self.sentinel, "check_god_mode",
                return_value={
                    "active": False,
                    "reason": None,
                    "operator": None,
                    "expires_utc": None,
                    "locked_hour": None,
                },
            ):
                result = self.sentinel.assess_human_cost()
                self.assertEqual(result, "AVAILABLE")
                self.assertTrue(status_path.exists())
                payload = status_path.read_text(encoding="utf-8")
                self.assertIn('"status": "NOMINAL"', payload)
                self.assertIn('"god_mode_active": false', payload)

    def test_assess_human_cost_uses_valid_god_mode_hour_override(self) -> None:
        denver = pytz.timezone("America/Denver")
        fixed_now = denver.localize(datetime(2026, 4, 18, 13, 30, 0))
        FixedDateTime.fixed_now = fixed_now

        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "sentinel_status.json"
            with patch.object(self.sentinel, "STATUS_PATH", status_path), patch.object(
                self.sentinel, "datetime", FixedDateTime
            ), patch.object(
                self.sentinel, "check_god_mode",
                return_value={
                    "active": True,
                    "reason": None,
                    "operator": "zoagrad",
                    "expires_utc": "2026-04-18T20:00:00+00:00",
                    "locked_hour": 3,
                },
            ):
                result = self.sentinel.assess_human_cost()
                self.assertEqual(result, "FATIGUE_RISK")
                payload = status_path.read_text(encoding="utf-8")
                self.assertIn('"status": "FATIGUE_BREACH"', payload)
                self.assertIn('"god_mode_operator": "zoagrad"', payload)


if __name__ == "__main__":
    unittest.main()
