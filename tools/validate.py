#!/usr/bin/env python3
"""Validate the built pstacky package. Exit 1 and list every problem otherwise."""

from __future__ import annotations

import json
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = "docs/harness/hermes.md"
ADAPTER_LINE = (
    "In Hermes, read [the pstacky adapter](../../docs/harness/hermes.md) once "
    "per session before you follow this file. It maps the Cursor names in pstack "
    "to Hermes tools."
)
DESLOP = "deslop"
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LINK = re.compile(r"\]\(([^)\s]+?)(#[^)]*)?\)")
FENCE = re.compile(r"```.*?```", re.S)


def frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip().strip('"')
    return out


def skill_dirs(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("skills/*/SKILL.md"))


def package_paths(root: Path) -> list[Path]:
    """Every shipped file, excluding tooling, the spec and the vendor checkout."""
    out: list[Path] = []
    for base in ("skills", "agents", "docs/guide", "docs/harness"):
        out.extend(p for p in (root / base).rglob("*") if p.is_file())
    for name in ("README.md", "NOTICE", "LICENSE", "plugin.json"):
        if (root / name).is_file():
            out.append(root / name)
    return sorted(out)


def markdown_paths(root: Path) -> list[Path]:
    return [
        p
        for p in package_paths(root)
        if p.suffix == ".md" and p.relative_to(root).as_posix().startswith(
            ("skills/", "docs/guide/", "docs/harness/")
        )
    ]


def validate(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    adapter_path = root / ADAPTER
    if not adapter_path.is_file():
        return [f"missing {ADAPTER}"]
    adapter = adapter_path.read_text()

    manifest_path = root / "plugin.json"
    if not manifest_path.is_file():
        problems.append("missing plugin.json")
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"plugin.json is not JSON: {exc}")
            manifest = {}
        for key in ("$schema", "name", "version", "description", "license"):
            if not manifest.get(key):
                problems.append(f"plugin.json is missing {key}")
        if manifest.get("name") != "pstacky":
            problems.append("plugin.json name is not pstacky")
        if manifest.get("license") != "MIT":
            problems.append("plugin.json license is not MIT")

    skills = skill_dirs(root)
    if len(skills) != 59:
        problems.append(f"expected 59 skills, found {len(skills)}")
    names: set[str] = set()

    for skill in skills:
        name = skill.name
        text = (skill / "SKILL.md").read_text()
        meta = frontmatter(text)
        if name in names:
            problems.append(f"duplicate skill {name}")
        names.add(name)
        if not KEBAB.match(name):
            problems.append(f"{name}: directory name is not kebab-case")
        if meta.get("name") != name:
            problems.append(f"{name}: frontmatter name is {meta.get('name')!r}")
        if not meta.get("description"):
            problems.append(f"{name}: frontmatter has no description")

        has_line = ADAPTER_LINE in text
        if name == DESLOP:
            if has_line:
                problems.append("deslop must not carry the adapter line")
            continue
        if not has_line:
            problems.append(f"{name}: missing adapter line")
        if text.count(ADAPTER_LINE) != 1:
            problems.append(f"{name}: adapter line appears {text.count(ADAPTER_LINE)} times")

    # TERMS: every term used in a skill has a row in the adapter
    sys.path.insert(0, str(root / "tools"))
    from terms import TERMS  # noqa: PLC0415

    for key, _ in TERMS:
        if key not in adapter:
            problems.append(f"adapter has no row for {key}")
    for path in markdown_paths(root):
        text = path.read_text(errors="replace")
        rel = path.relative_to(root).as_posix()
        for key, pattern in TERMS:
            if re.search(pattern, text) and key not in adapter:
                problems.append(f"{rel}: uses {key}, adapter has no row")

    # placeholders and absolute host paths in generated content
    for path in markdown_paths(root):
        text = path.read_text(errors="replace")
        rel = path.relative_to(root).as_posix()
        for token in ("{{", "TODO", "FIXME"):
            if token in text:
                problems.append(f"{rel}: contains placeholder {token}")
        if "/home/" in text or "C:\\Users" in text:
            problems.append(f"{rel}: contains an absolute host path")

    # every relative link resolves inside the package
    shipped = package_paths(root)
    files = {p.relative_to(root).as_posix() for p in shipped}
    dirs = set()
    for base in ("skills", "agents", "docs/guide", "docs/harness"):
        for path in (root / base).rglob("*"):
            if path.is_dir():
                dirs.add(path.relative_to(root).as_posix())
    for path in markdown_paths(root):
        rel = path.relative_to(root).as_posix()
        text = FENCE.sub("", path.read_text(errors="replace"))
        for match in LINK.finditer(text):
            target = match.group(1)
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
            if resolved in files or resolved in dirs:
                continue
            problems.append(f"{rel}: broken relative link {target}")

    # agents and guide shipped
    for agent in ("poteto-agent.md", "comment-sicko.md"):
        if not (root / "agents" / agent).is_file():
            problems.append(f"missing agents/{agent}")
    for skill, agent in (
        ("poteto-mode", "poteto-agent.md"),
        ("poteto-help", "poteto-agent.md"),
        ("no-comments", "comment-sicko.md"),
    ):
        if not (root / "skills" / skill / "references" / "agents" / agent).is_file():
            problems.append(f"{skill}: missing references/agents/{agent}")
    if not any((root / "docs" / "guide").glob("*.md")):
        problems.append("docs/guide is empty")

    return problems


def main() -> None:
    problems = validate()
    if problems:
        print(f"validate: {len(problems)} problem(s)", file=sys.stderr)
        for problem in problems[:80]:
            print(f"  {problem}", file=sys.stderr)
        raise SystemExit(1)
    print("validate: clean")


if __name__ == "__main__":
    main()
