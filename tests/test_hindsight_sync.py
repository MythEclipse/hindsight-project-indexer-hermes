"""Tests for Hindsight caching and sync logic."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from hindsight_project_indexer.hindsight_sync import (
    load_hindsight_config,
    mark_dirty,
    get_project_index
)


class TestHindsightSync(unittest.TestCase):
    def test_load_hindsight_config(self):
        cfg = load_hindsight_config()
        self.assertIn("api_url", cfg)
        self.assertIn("bank_id", cfg)

    def test_caching_and_dirty_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "package.json").write_text('{"name": "test-cache"}')

            with patch("hindsight_project_indexer.hindsight_sync.sync_to_hindsight") as mock_sync:
                summary1 = get_project_index(tmp_path, force_refresh=False)
                self.assertEqual(mock_sync.call_count, 1)

                # Second call should hit in-memory / disk cache
                summary2 = get_project_index(tmp_path, force_refresh=False)
                self.assertEqual(mock_sync.call_count, 1)

                # Mark dirty and call again
                mark_dirty(tmp_path)
                summary3 = get_project_index(tmp_path, force_refresh=False)
                self.assertEqual(summary3["fingerprint"], summary1["fingerprint"])


if __name__ == "__main__":
    unittest.main()
