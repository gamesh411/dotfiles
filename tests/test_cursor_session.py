"""The macOS CLI session lives in the Keychain; the app's stored token may be encrypted."""
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("capacity_cursor", ROOT / "dot_local/lib/agent_capacity/cursor.py")
assert SPEC is not None and SPEC.loader is not None
cursor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cursor)


def keychain(stdout="", returncode=0):
    return subprocess.CompletedProcess(["security"], returncode, stdout=stdout, stderr="")


class MacSessionTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        database = self.home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
        database.parent.mkdir(parents=True)
        with sqlite3.connect(database) as db:
            db.execute("CREATE TABLE ItemTable (key TEXT, value BLOB)")
            db.execute("INSERT INTO ItemTable VALUES ('cursorAuth/accessToken', 'v1abcdefgh:10:c2VjcmV0+/x')")
        patches = [patch.object(cursor.sys, "platform", "darwin"),
                   patch.object(cursor.Path, "home", return_value=self.home)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_keychain_cli_token_precedes_the_app_database(self):
        with patch.object(cursor.subprocess, "run", return_value=keychain("a.b.c\n")) as run:
            self.assertEqual(cursor.native_token(), ("a.b.c", "cursor_cli_native_session"))
        self.assertEqual(run.call_args.args[0][:2], ["/usr/bin/security", "find-generic-password"])

    def test_encrypted_app_token_is_reported_as_such(self):
        for outcome in (keychain(returncode=44), subprocess.TimeoutExpired("security", 5)):
            with self.subTest(outcome=type(outcome).__name__), \
                    patch.object(cursor.subprocess, "run", side_effect=[outcome]):
                with self.assertRaises(cursor.ProbeError) as raised:
                    cursor.native_token()
                self.assertEqual(str(raised.exception), "native_session_encrypted")


if __name__ == "__main__":
    unittest.main()
