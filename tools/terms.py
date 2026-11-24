"""Cursor terms that must have a row in the Hermes adapter.

Each entry is (adapter_key, regex). The generator refuses to build when a skill
uses a term whose key is absent from docs/harness/hermes.md, so an upstream
release that introduces a new Cursor primitive fails loudly instead of shipping
an instruction the agent cannot follow.
"""

from __future__ import annotations

TERMS: list[tuple[str, str]] = [
    ("Task", r"\bTask\b"),
    ("AskQuestion", r"\bAskQuestion\b"),
    ("TodoWrite", r"\bTodoWrite\b"),
    ("subagent_type", r"subagent_type"),
    ("run_in_background", r"run_in_background"),
    ("readonly", r"\breadonly\b"),
    ("cloud_base_branch", r"cloud_base_branch"),
    ("generalPurpose", r"\bgeneralPurpose\b"),
    ("poteto-agent", r"poteto-agent"),
    ("comment-sicko", r"comment-sicko"),
    (".cursor/", r"\.cursor/"),
    ("pstack-models.mdc", r"pstack-models\.mdc"),
    ("Bugbot", r"\bBugbot\b"),
    ("Canvas", r"\bCanvas\b"),
    ("/loop", r"/loop\b"),
    ("cursor-team-kit", r"cursor-team-kit"),
]
