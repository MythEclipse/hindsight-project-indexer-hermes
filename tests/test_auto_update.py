"""Tests for plugin self-updater module."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from hindsight_project_indexer.auto_update import check_and_update, get_plugin_root


class TestAutoUpdate(unittest.TestCase):
    def test_get_plugin_root(self):
        root = get_plugin_root()
        self.assertTrue((root / "plugin.yaml").exists() or (root / "hindsight_project_indexer").exists())

    def test_non_git_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("hindsight_project_indexer.auto_update.get_plugin_root", return_value=Path(tmpdir)):
                res = check_and_update(force=True)
                self.assertEqual(res["status"], "not_git_repo")


if __name__ == "__main__":
    unittest.main()
