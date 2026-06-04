from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.storage.database_storage import DatabaseStorageBackend


class DatabaseStorageBackendTests(unittest.TestCase):
    def test_sqlite_account_incremental_writes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "accounts.db"
            backend = DatabaseStorageBackend(f"sqlite:///{db_path}")
            try:
                backend.upsert_accounts([
                    {"access_token": "token-a", "status": "normal", "quota": 10},
                    {"access_token": "token-b", "status": "error", "quota": 0},
                ])
                self.assertEqual(len(backend.load_accounts()), 2)

                backend.upsert_accounts([
                    {"access_token": "token-a", "status": "limited", "quota": 0},
                ])
                accounts = {item["access_token"]: item for item in backend.load_accounts()}
                self.assertEqual(accounts["token-a"]["status"], "limited")
                self.assertEqual(accounts["token-b"]["status"], "error")

                backend.replace_account(
                    {"access_token": "token-c", "status": "normal", "quota": 5},
                    old_access_token="token-a",
                )
                accounts = {item["access_token"]: item for item in backend.load_accounts()}
                self.assertNotIn("token-a", accounts)
                self.assertIn("token-c", accounts)

                removed = backend.delete_accounts(["token-b", "missing"])
                self.assertEqual(removed, 1)
                self.assertEqual(
                    [item["access_token"] for item in backend.load_accounts()],
                    ["token-c"],
                )
            finally:
                backend.engine.dispose()


if __name__ == "__main__":
    unittest.main()
