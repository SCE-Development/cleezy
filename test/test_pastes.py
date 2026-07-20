import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# this allows imports from the modules folder to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from modules import sqlite_helpers

# server.py requires command-line args when imported.
# These fake args let the test import server.py without crashing.
TEST_ROOT_DIR = tempfile.TemporaryDirectory()
TEST_DB_PATH = os.path.join(TEST_ROOT_DIR.name, "test.db")
TEST_QR_CACHE_DIR = tempfile.TemporaryDirectory()

with mock.patch.object(
    sys,
    "argv",
    [
        "server.py",
        "--database-file-path",
        TEST_DB_PATH,
        "--qr-code-cache-path",
        TEST_QR_CACHE_DIR.name,
        "--qr-code-base-url",
        "http://localhost:8000",
    ],
):
    import server


class TestPasteEndpoints(unittest.TestCase):
    def test_create_paste_rejects_file_larger_than_10mb(self):
        large_content = b"a" * ((10 * 1024 * 1024) + 1)

        with TestClient(server.app) as client:
            response = client.post(
                "/paste/create",
                files={"file": ("large.txt", large_content, "text/plain")},
            )

        self.assertEqual(response.status_code, 400)

    def test_create_paste_creates_file_and_database_row(self):
        with tempfile.TemporaryDirectory() as tmp_root:
            tmp_db_path = os.path.join(tmp_root, "test.db")
            tmp_pastes_dir = os.path.join(tmp_root, "pastes")

            sqlite_helpers.maybe_create_table(tmp_db_path)

            with mock.patch.object(server, "DATABASE_FILE", tmp_db_path):
                with mock.patch.object(server, "PASTES_DIR", Path(tmp_pastes_dir)):
                    with mock.patch("server.secrets.token_hex", return_value="fe80df"):
                        with TestClient(server.app) as client:
                            response = client.post(
                                "/paste/create",
                                files={
                                    "file": (
                                        "example.txt",
                                        b"hello paste",
                                        "text/plain",
                                    )
                                },
                            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["paste_id"], "fe80df")
            self.assertEqual(response.json()["filename"], "example.txt")

            paste_path = Path(tmp_pastes_dir) / "fe80df"
            self.assertTrue(paste_path.exists())
            self.assertEqual(paste_path.read_bytes(), b"hello paste")

            db = sqlite3.connect(tmp_db_path)
            cursor = db.cursor()
            cursor.execute(
                "SELECT paste_id, title FROM pastes WHERE paste_id = ?",
                ("fe80df",),
            )
            row = cursor.fetchone()
            cursor.close()
            db.close()

            self.assertIsNotNone(row)
            self.assertEqual(row[0], "fe80df")
            self.assertEqual(row[1], "example.txt")


if __name__ == "__main__":
    unittest.main()