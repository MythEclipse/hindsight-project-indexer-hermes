"""Tests for project structure and stack analyzer."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from hindsight_project_indexer.indexer import (
    find_project_root,
    get_project_fingerprint,
    analyze_tech_stack,
    generate_compact_tree,
    build_project_summary
)


class TestIndexer(unittest.TestCase):
    def test_find_project_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sub = tmp_path / "sub" / "deep"
            sub.mkdir(parents=True)

            self.assertIsNone(find_project_root(sub))

            # Add .git marker
            (tmp_path / ".git").mkdir()
            self.assertEqual(find_project_root(sub), tmp_path)

    def test_analyze_tech_stack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18.0.0", "typescript": "^5.0.0"}}')

            stack = analyze_tech_stack(tmp_path)
            self.assertIn("TypeScript", stack["languages"])
            self.assertIn("React", stack["frameworks"])
            self.assertIn("package.json", stack["manifests"])

    def test_compact_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "index.ts").write_text("console.log(1);")
            (tmp_path / "node_modules").mkdir()
            (tmp_path / "node_modules" / "foo").mkdir()

            tree = generate_compact_tree(tmp_path)
            self.assertIn("src/", tree)
            self.assertIn("index.ts", tree)
            self.assertNotIn("node_modules", tree)

    def test_build_project_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "README.md").write_text("# My Test App\nThis is a sample app.")
            (tmp_path / "Cargo.toml").write_text('[package]\nname = "my_app"\n[dependencies]\ntokio = "1"')

            summary = build_project_summary(tmp_path)
            self.assertEqual(summary["project_name"], tmp_path.name)
            self.assertIn("Rust", summary["stack"]["languages"])
            self.assertIn("My Test App", summary["readme"])
            self.assertIsNotNone(summary["fingerprint"])


if __name__ == "__main__":
    unittest.main()
