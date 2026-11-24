"""Generator contract tests. Stdlib only: python3 -m unittest discover -s tests"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import generate  # noqa: E402

VENDOR_READY = (ROOT / "vendor" / "cursor-plugins" / ".git").exists()


class AdapterLineTests(unittest.TestCase):
    def test_after_h1(self) -> None:
        text = "---\nname: x\ndescription: d\n---\n\n# Title\n\nBody.\n"
        out = generate.insert_adapter_line(text, "x")
        self.assertIn("# Title\n\n" + generate.ADAPTER_LINE + "\n\nBody.", out)

    def test_after_frontmatter_without_h1(self) -> None:
        text = "---\nname: bro\ndescription: d\n---\n\nBody.\n"
        out = generate.insert_adapter_line(text, "bro")
        self.assertTrue(out.startswith("---\nname: bro\ndescription: d\n---\n\n" + generate.ADAPTER_LINE))

    def test_idempotent(self) -> None:
        text = "---\nname: x\ndescription: d\n---\n\n# T\n\nBody.\n"
        once = generate.insert_adapter_line(text, "x")
        twice = generate.insert_adapter_line(once, "x")
        self.assertEqual(once, twice)
        self.assertEqual(once.count(generate.ADAPTER_LINE), 1)

    def test_missing_structure_raises(self) -> None:
        with self.assertRaises(SystemExit):
            generate.insert_adapter_line("no frontmatter, no heading\n", "bad")


class LinkTests(unittest.TestCase):
    def test_main_links_pinned(self) -> None:
        text = "see https://github.com/cursor/plugins/blob/main/pstack/agents/x.md"
        out = generate.pin_github_links(text, "abc123")
        self.assertIn("/blob/abc123/pstack/agents/x.md", out)
        self.assertNotIn("/blob/main/", out)


@unittest.skipUnless(VENDOR_READY, "vendor/cursor-plugins not cloned; run tools/vendor.sh")
class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = generate.build()

    def test_deterministic(self) -> None:
        again = generate.build()
        self.assertEqual(self.build.files, again.files)

    def test_counts(self) -> None:
        skills = [r for r in self.build.files if r.count("/") == 2 and r.endswith("/SKILL.md")]
        self.assertEqual(len(skills), 59)
        self.assertNotIn("skills/make-bot-ui/SKILL.md", self.build.files)
        self.assertIn("skills/deslop/SKILL.md", self.build.files)
        self.assertEqual(
            len([r for r in self.build.files if r.endswith("references/pstacky-adapter.md")]),
            58,
        )

    def test_deslop_untouched(self) -> None:
        upstream = (
            ROOT / "vendor" / "cursor-plugins" / "cursor-team-kit" / "skills" / "deslop" / "SKILL.md"
        ).read_bytes()
        self.assertEqual(self.build.files["skills/deslop/SKILL.md"], upstream)

    def test_skills_are_byte_identical_except_adapter_line(self) -> None:
        upstream = ROOT / "vendor" / "cursor-plugins" / "pstack" / "skills" / "interrogate" / "SKILL.md"
        original = upstream.read_text()
        built = self.build.files["skills/interrogate/SKILL.md"].decode()
        self.assertEqual(built.replace("\n\n" + generate.ADAPTER_LINE, "", 1), original)

    def test_manifest(self) -> None:
        manifest = json.loads(self.build.files["plugin.json"])
        self.assertEqual(manifest["name"], "pstacky")
        self.assertEqual(manifest["license"], "MIT")

    def test_tree_matches_build(self) -> None:
        self.assertEqual(generate.diff_against_disk(self.build), [])


if __name__ == "__main__":
    unittest.main()
