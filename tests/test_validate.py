"""Validator contract tests: clean tree passes, each defect is caught."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import validate  # noqa: E402

BUILT = (ROOT / "skills").is_dir() and (ROOT / "docs" / "harness" / "hermes.md").is_file()


@unittest.skipUnless(BUILT, "package not built; run tools/generate.py")
class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pstacky-validate-"))
        for base in ("skills", "agents", "docs"):
            shutil.copytree(ROOT / base, self.tmp / base)
        for name in ("plugin.json", "README.md", "NOTICE", "LICENSE"):
            shutil.copy2(ROOT / name, self.tmp / name)
        shutil.copytree(ROOT / "tools", self.tmp / "tools")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean(self) -> None:
        self.assertEqual(validate.validate(self.tmp), [])

    def test_missing_adapter_line(self) -> None:
        path = self.tmp / "skills" / "interrogate" / "SKILL.md"
        path.write_text(path.read_text().replace(validate.ADAPTER_LINE, ""))
        problems = validate.validate(self.tmp)
        self.assertTrue(any("interrogate: missing adapter line" in p for p in problems), problems)

    def test_broken_relative_link(self) -> None:
        path = self.tmp / "skills" / "bro" / "SKILL.md"
        path.write_text(path.read_text() + "\n[gone](../nope/SKILL.md)\n")
        problems = validate.validate(self.tmp)
        self.assertTrue(any("broken relative link" in p for p in problems), problems)

    def test_deslop_must_stay_plain(self) -> None:
        path = self.tmp / "skills" / "deslop" / "SKILL.md"
        path.write_text(path.read_text() + "\n" + validate.ADAPTER_LINE + "\n")
        problems = validate.validate(self.tmp)
        self.assertTrue(any("deslop must not carry" in p for p in problems), problems)

    def test_manifest_name(self) -> None:
        path = self.tmp / "plugin.json"
        path.write_text(path.read_text().replace('"pstacky"', '"other"'))
        problems = validate.validate(self.tmp)
        self.assertTrue(any("name is not pstacky" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
