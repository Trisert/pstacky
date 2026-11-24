#!/usr/bin/env python3
"""Build the pstacky package from the pinned cursor/plugins checkout.

Usage:
  python3 tools/generate.py           write the package into the repo
  python3 tools/generate.py --check   rebuild in memory, exit 1 on any difference
  python3 tools/generate.py --sync SHA  move UPSTREAM_PIN to SHA and rebuild

The build is a pure function of (vendor checkout at the pin, docs/harness/hermes.md,
tools/terms.py). No timestamps, no absolute paths: running it twice produces
identical bytes.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "cursor-plugins"
PIN_FILE = ROOT / "UPSTREAM_PIN"
ADAPTER_SRC = ROOT / "docs" / "harness" / "hermes.md"

PLUGIN_NAME = "pstacky"
PACKAGE_VERSION = "0.1.0"
DESCRIPTION = (
    "pstack for Hermes Agent, 1:1: every upstream skill byte for byte, a "
    "Cursor-to-Hermes adapter that works single-model or routed, and deslop."
)

ADAPTER_LINE = (
    "In Hermes, read [the pstacky adapter](../../docs/harness/hermes.md) once "
    "per session before you follow this file. It maps the Cursor names in pstack "
    "to Hermes tools."
)

# Companion skill, shipped from cursor-team-kit at the same commit.
DESLOP_PATH = "cursor-team-kit/skills/deslop"

# Install-scanner verdict: `curl | sudo sh` reads as privilege escalation.
# Both mature ports exclude it too.
SKIP_SKILLS = {"make-bot-ui"}

# Skills that spawn an agent file; the agent is copied into the skill's references.
AGENT_FOR_SKILL = {
    "poteto-mode": "poteto-agent.md",
    "poteto-help": "poteto-agent.md",
    "no-comments": "comment-sicko.md",
}

GENERATED_ROOTS = ("skills/", "agents/", "docs/guide/", "plugin.json")

_LINK = re.compile(r"\]\(([^)\s]+?)(#[^)]*)?\)")
_H1 = re.compile(r"^# .+$", re.M)
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_GH_MAIN = re.compile(r"https://github\.com/cursor/plugins/blob/main/pstack/")


@dataclass
class Build:
    files: dict[str, bytes] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add(self, rel: str, data: bytes) -> None:
        if rel in self.files and self.files[rel] != data:
            raise SystemExit(f"generate: two sources write {rel} with different content")
        self.files[rel] = data


def load_pin() -> dict[str, str]:
    pin = json.loads(PIN_FILE.read_text())
    for key in ("repo", "sha", "pstack_version"):
        if not pin.get(key):
            raise SystemExit(f"generate: UPSTREAM_PIN is missing {key}")
    return pin


def check_vendor(pin: dict[str, str]) -> Path:
    if not (VENDOR / ".git").exists():
        raise SystemExit(f"generate: vendor checkout missing at {VENDOR}; run tools/vendor.sh")
    head = (VENDOR / ".git" / "HEAD").read_text().strip()
    actual = head.removeprefix("ref: refs/heads/")
    if actual != pin["sha"]:
        raise SystemExit(f"generate: vendor is at {actual[:12]}, expected {pin['sha'][:12]}")
    return VENDOR / "pstack"


def copy_tree(build: Build, src: Path, prefix: str) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_dir() or path.name == ".DS_Store":
            continue
        rel = f"{prefix}/{path.relative_to(src).as_posix()}"
        build.add(rel, path.read_bytes())


def insert_adapter_line(text: str, where: str) -> str:
    if ADAPTER_LINE in text:
        return text
    match = _H1.search(text)
    if match:
        end = match.end()
        return f"{text[:end]}\n\n{ADAPTER_LINE}{text[end:]}"
    front = _FRONTMATTER.match(text)
    if front:
        end = front.end()
        return f"{text[:end]}\n{ADAPTER_LINE}\n{text[end:]}"
    raise SystemExit(f"generate: {where} has neither frontmatter nor H1 for the adapter line")


def pin_github_links(text: str, sha: str) -> str:
    return _GH_MAIN.sub(
        f"https://github.com/cursor/plugins/blob/{sha}/pstack/", text
    )


def rewrite_escaping_links(pkg: Build, pin: dict[str, str], upstream: Path) -> None:
    """Relative links that resolve outside the package point at the pinned GitHub tree."""
    sha = pin["sha"]
    for rel in sorted(pkg.files):
        if not rel.endswith(".md"):
            continue
        text = pkg.files[rel].decode("utf-8", "replace")
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            target = match.group(1)
            anchor = match.group(2) or ""
            if target.startswith(("#", "http://", "https://", "mailto:")):
                return match.group(0)
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
            if (
                resolved in pkg.files
                or any(f.startswith(resolved + "/") for f in pkg.files)
                or (ROOT / resolved).is_file()
                or (ROOT / resolved).is_dir()
            ):
                return match.group(0)
            candidate = upstream / resolved
            if candidate.is_file() or candidate.is_dir():
                changed = True
                return f"](https://github.com/cursor/plugins/blob/{sha}/pstack/{resolved}{anchor})"
            pkg.warnings.append(f"{rel}: link target not shipped and not upstream: {target}")
            return match.group(0)

        text = _LINK.sub(repl, text)
        if changed:
            pkg.files[rel] = text.encode()


def build() -> Build:
    pin = load_pin()
    upstream = check_vendor(pin)
    adapter = ADAPTER_SRC.read_text()
    build_ = Build()

    # 1. skills, byte for byte, one adapter line + one adapter copy each
    skills_src = upstream / "skills"
    skill_names = sorted(
        p.name
        for p in skills_src.iterdir()
        if (p / "SKILL.md").is_file() and p.name not in SKIP_SKILLS
    )
    for name in skill_names:
        src = skills_src / name
        for path in sorted(src.rglob("*")):
            if path.is_dir() or path.name == ".DS_Store":
                continue
            rel = f"skills/{name}/{path.relative_to(src).as_posix()}"
            data = path.read_bytes()
            if path.name == "SKILL.md":
                data = insert_adapter_line(data.decode(), f"skills/{name}/SKILL.md").encode()
            build_.add(rel, data)
        agent = AGENT_FOR_SKILL.get(name)
        if agent:
            build_.add(
                f"skills/{name}/references/agents/{agent}",
                (upstream / "agents" / agent).read_bytes(),
            )

    # 2. deslop: companion skill, no adapter line, no adapter copy
    deslop = VENDOR / DESLOP_PATH
    if not (deslop / "SKILL.md").is_file():
        raise SystemExit(f"generate: {DESLOP_PATH}/SKILL.md missing from the vendor checkout")
    build_.add("skills/deslop/SKILL.md", (deslop / "SKILL.md").read_bytes())

    # 3. agents and guide (the adapter is source, not generated)
    for path in sorted((upstream / "agents").glob("*.md")):
        build_.add(f"agents/{path.name}", path.read_bytes())
    copy_tree(build_, upstream / "docs" / "guide", "docs/guide")

    # 4. manifest
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": PLUGIN_NAME,
        "version": PACKAGE_VERSION,
        "description": DESCRIPTION,
        "author": {"name": "Nicola Destro"},
        "license": "MIT",
        "keywords": [
            "pstack",
            "poteto-mode",
            "hermes",
            "skills",
            "workflow",
            "delegation",
            "verification",
        ],
    }
    build_.add("plugin.json", (json.dumps(manifest, indent=2) + "\n").encode())

    # 5. links, then the guard for unmapped Cursor terms
    for rel in list(build_.files):
        if rel.endswith(".md"):
            build_.files[rel] = pin_github_links(
                build_.files[rel].decode("utf-8", "replace"), pin["sha"]
            ).encode()
    rewrite_escaping_links(build_, pin, upstream)
    check_terms(build_, adapter)
    return build_


def check_terms(build_: Build, adapter: str) -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    from terms import TERMS  # noqa: PLC0415

    missing_keys = [key for key, _ in TERMS if key not in adapter]
    if missing_keys:
        raise SystemExit(f"generate: adapter has no row for: {', '.join(missing_keys)}")
    problems: list[str] = []
    for rel, data in sorted(build_.files.items()):
        if not rel.endswith(".md"):
            continue
        text = data.decode("utf-8", "replace")
        for key, pattern in TERMS:
            if re.search(pattern, text) and key not in adapter:
                problems.append(f"{rel} uses {key}, adapter has no row")
    if problems:
        raise SystemExit("generate: unmapped Cursor terms:\n  " + "\n  ".join(problems))


def generated_files(build_: Build) -> dict[str, bytes]:
    return {
        rel: data
        for rel, data in build_.files.items()
        if rel.startswith(GENERATED_ROOTS)
    }


def diff_against_disk(build_: Build) -> list[str]:
    want = generated_files(build_)
    problems = []
    for rel in sorted(want):
        dest = ROOT / rel
        if not dest.is_file():
            problems.append(f"missing: {rel}")
        elif dest.read_bytes() != want[rel]:
            problems.append(f"differs: {rel}")
    for base in ("skills", "agents", "docs/guide"):
        root = ROOT / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and rel not in want:
                problems.append(f"stale: {rel}")
    return problems


def write(build_: Build) -> tuple[int, int]:
    want = generated_files(build_)
    written = removed = 0
    for rel, data in sorted(want.items()):
        dest = ROOT / rel
        if dest.is_file() and dest.read_bytes() == data:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        written += 1
    # remove generated files that no longer belong
    for base in ("skills", "agents", "docs/guide"):
        root = ROOT / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), reverse=True):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and rel not in want:
                path.unlink()
                removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    return written, removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--sync", metavar="SHA")
    args = parser.parse_args()

    if args.sync:
        pin = json.loads(PIN_FILE.read_text())
        pin["sha"] = args.sync
        PIN_FILE.write_text(json.dumps(pin, indent=2) + "\n")

    build_ = build()
    if build_.warnings:
        for warning in build_.warnings:
            print(f"warning: {warning}", file=sys.stderr)

    if args.check:
        problems = diff_against_disk(build_)
        if problems:
            print("generate --check: build is stale", file=sys.stderr)
            for problem in problems[:40]:
                print(f"  {problem}", file=sys.stderr)
            raise SystemExit(1)
        print(f"generate --check: clean ({len(generated_files(build_))} files)")
        return

    written, removed = write(build_)
    skills = len([r for r in build_.files if re.fullmatch(r"skills/[^/]+/SKILL\.md", r)])
    print(f"generate: {skills} skills, {len(build_.files)} files, {written} written, {removed} removed")


if __name__ == "__main__":
    main()
