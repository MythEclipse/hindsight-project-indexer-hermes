"""Tests for project structure and stack analyzer."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from hindsight_project_indexer.indexer import (
    find_project_root,
    get_project_fingerprint,
    scan_universal_project,
    generate_compact_tree,
    build_project_summary,
    extract_public_api_map
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

    def test_scan_universal_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "Cargo.toml").write_text('[package]\nname = "my_rust_app"')
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.rs").write_text('fn main() {}')
            (tmp_path / "model.gguf").write_text('dummy')

            info = scan_universal_project(tmp_path)
            lang_names = [l for l, c in info["languages"]]
            self.assertIn("Rust", lang_names)
            self.assertIn("Rust (Cargo)", info["manifests"])
            self.assertIn("build", info["commands"])
            # GGUF artifact triggers ML domain
            self.assertTrue(any("ML" in d for d in info["domains"]))

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
            (tmp_path / "CLAUDE.md").write_text("## Rules\n- Never commit secrets to repository\n- Always run tests before pushing")
            (tmp_path / ".env.example").write_text("DATABASE_URL=postgres://...\nPORT=8080")
            (tmp_path / "apps").mkdir()
            (tmp_path / "packages").mkdir()

            summary = build_project_summary(tmp_path)
            self.assertEqual(summary["project_name"], tmp_path.name)
            self.assertIn("My Test App", summary["readme"])
            self.assertIsNotNone(summary["fingerprint"])
            self.assertIn("Monorepo / Workspaces", summary["arch_patterns"])
            self.assertTrue(any("Never commit secrets" in r for r in summary["rules_data"]["rules"]))
            self.assertIn("DATABASE_URL", summary["env_keys"])

    def test_extract_public_api_map(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "lib.rs").write_text("pub mod engine;\npub fn compute_result() -> i32 { 42 }")

            api = extract_public_api_map(tmp_path)
            self.assertIn("src/lib.rs", api)
            self.assertTrue(any("pub fn compute_result" in sym for sym in api["src/lib.rs"]))

    def test_lod_modes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "Cargo.toml").write_text('[package]\nname = "lod_test"')
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.rs").write_text("fn main() {}")

            standard = build_project_summary(tmp_path, mode="standard")
            deep = build_project_summary(tmp_path, mode="deep")

            self.assertEqual(standard["mode"], "standard")
            self.assertEqual(deep["mode"], "deep")
            self.assertIn("(Deep Mode)", deep["formatted_context"])
            self.assertNotIn("(Deep Mode)", standard["formatted_context"])


if __name__ == "__main__":
    unittest.main()
