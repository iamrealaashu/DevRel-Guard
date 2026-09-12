"""Unified Git Diff Parser for DevRel Guard."""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DiffLine(BaseModel):
    origin: str  # '+', '-', ' '
    content: str
    old_lineno: Optional[int] = None
    new_lineno: Optional[int] = None


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: List[DiffLine] = Field(default_factory=list)


class FileDiff(BaseModel):
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    is_new: bool = False
    is_deleted: bool = False
    is_modified: bool = True
    hunks: List[DiffHunk] = Field(default_factory=list)

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or "unknown"

    @property
    def is_dependency_manifest(self) -> bool:
        filename = (self.path or "").lower()
        return any(
            filename.endswith(dep)
            for dep in [
                "requirements.txt",
                "pyproject.toml",
                "setup.cfg",
                "setup.py",
                "pipfile",
                "poetry.lock",
                "package.json",
            ]
        )

    def get_added_lines(self) -> List[str]:
        added = []
        for hunk in self.hunks:
            for line in hunk.lines:
                if line.origin == "+":
                    added.append(line.content)
        return added

    def get_removed_lines(self) -> List[str]:
        removed = []
        for hunk in self.hunks:
            for line in hunk.lines:
                if line.origin == "-":
                    removed.append(line.content)
        return removed


class ParsedPRDiff(BaseModel):
    raw_diff: str
    files: List[FileDiff] = Field(default_factory=list)

    def get_manifest_diffs(self) -> List[FileDiff]:
        return [f for f in self.files if f.is_dependency_manifest]

    def get_source_diffs(self) -> List[FileDiff]:
        return [f for f in self.files if not f.is_dependency_manifest]


def parse_unified_diff(raw_diff: str) -> ParsedPRDiff:
    """Parse unified git diff format into structured FileDiff and DiffHunk objects."""
    if not raw_diff or not raw_diff.strip():
        return ParsedPRDiff(raw_diff="", files=[])

    files: List[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None
    old_lineno = 0
    new_lineno = 0

    lines = raw_diff.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # Git diff header
        if line.startswith("diff --git "):
            if current_file:
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                files.append(current_file)

            parts = line.split(" ")
            old_p = parts[2][2:] if len(parts) > 2 and parts[2].startswith("a/") else None
            new_p = parts[3][2:] if len(parts) > 3 and parts[3].startswith("b/") else None
            current_file = FileDiff(old_path=old_p, new_path=new_p)
            i += 1
            continue

        if current_file:
            if line.startswith("--- "):
                if line.startswith("--- /dev/null"):
                    current_file.is_new = True
                elif not current_file.old_path:
                    current_file.old_path = line[4:].strip().lstrip("a/")
                i += 1
                continue
            elif line.startswith("+++ "):
                if line.startswith("+++ /dev/null"):
                    current_file.is_deleted = True
                elif not current_file.new_path:
                    current_file.new_path = line[4:].strip().lstrip("b/")
                i += 1
                continue

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            hunk_match = re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)", line)
            if hunk_match:
                if current_hunk:
                    current_file.hunks.append(current_hunk)

                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                header = hunk_match.group(5).strip()

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=header,
                    lines=[],
                )
                old_lineno = old_start
                new_lineno = new_start
                i += 1
                continue

            if current_hunk:
                if line.startswith("+") and not line.startswith("+++"):
                    current_hunk.lines.append(
                        DiffLine(origin="+", content=line[1:], new_lineno=new_lineno)
                    )
                    new_lineno += 1
                elif line.startswith("-") and not line.startswith("---"):
                    current_hunk.lines.append(
                        DiffLine(origin="-", content=line[1:], old_lineno=old_lineno)
                    )
                    old_lineno += 1
                elif line.startswith(" ") or line == "":
                    content = line[1:] if line.startswith(" ") else ""
                    current_hunk.lines.append(
                        DiffLine(
                            origin=" ",
                            content=content,
                            old_lineno=old_lineno,
                            new_lineno=new_lineno,
                        )
                    )
                    old_lineno += 1
                    new_lineno += 1

        i += 1

    if current_file:
        if current_hunk:
            current_file.hunks.append(current_hunk)
        files.append(current_file)

    return ParsedPRDiff(raw_diff=raw_diff, files=files)
