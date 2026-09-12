"""Dependency change scanner and version bump extractor."""

from __future__ import annotations
import re
from typing import List, Optional, Tuple
from devrel_guard.core.models import DependencyChange
from devrel_guard.core.diff_parser import FileDiff, ParsedPRDiff


# Matchers for common dependency manifest formats:
# 1. requirements.txt: package==1.2.3, package>=1.2.3, etc.
REQ_LINE_RE = re.compile(
    r"^\s*([a-zA-Z0-9_\-\.]+)\s*([=><~^!]+)\s*([0-9a-zA-Z\.\-]+)",
    re.IGNORECASE,
)

# 2. pyproject.toml poetry / tool.poetry.dependencies:
# package = "^1.2.3" or package = ">=1.2.3" or "package>=1.2.3"
PYPROJECT_KV_RE = re.compile(
    r'^\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*=\s*["\']([=><~^!]*)\s*([0-9a-zA-Z\.\-]+)["\']',
    re.IGNORECASE,
)
PYPROJECT_DEP_ARRAY_RE = re.compile(
    r'["\']([a-zA-Z0-9_\-\.]+)\s*([=><~^!]+)\s*([0-9a-zA-Z\.\-]+)["\']',
    re.IGNORECASE,
)

# 3. package.json dependencies:
PACKAGE_JSON_RE = re.compile(
    r'^\s*["\'](@?[a-zA-Z0-9_\-\./]+)["\']\s*:\s*["\']([=><~^!]*)\s*([0-9a-zA-Z\.\-]+)["\']',
    re.IGNORECASE,
)


def extract_package_version_from_line(line: str, filename: str) -> Optional[Tuple[str, str]]:
    """Extract (package_name, version) from a single manifest line."""
    clean = line.strip()
    if clean.startswith("#") or clean.startswith("//"):
        return None

    fname = filename.lower()
    if "requirements" in fname or fname.endswith(".txt"):
        m = REQ_LINE_RE.match(clean)
        if m:
            return m.group(1).lower().replace("_", "-"), m.group(3)

    if "pyproject" in fname or fname.endswith(".toml"):
        m = PYPROJECT_KV_RE.match(clean)
        if m:
            return m.group(1).lower().replace("_", "-"), m.group(3)
        m2 = PYPROJECT_DEP_ARRAY_RE.search(clean)
        if m2:
            return m2.group(1).lower().replace("_", "-"), m2.group(3)

    if "package.json" in fname:
        m = PACKAGE_JSON_RE.match(clean)
        if m:
            return m.group(1).lower(), m.group(3)

    # General fallback
    m = REQ_LINE_RE.match(clean)
    if m:
        return m.group(1).lower().replace("_", "-"), m.group(3)

    return None


def is_major_or_breaking_bump(old_ver: str, new_ver: str) -> bool:
    """Determine if semver change represents a breaking transition."""
    def parse_semver_parts(v: str) -> List[int]:
        nums = []
        for part in re.split(r"[^\d]+", v):
            if part.isdigit():
                nums.append(int(part))
        return nums or [0]

    old_parts = parse_semver_parts(old_ver)
    new_parts = parse_semver_parts(new_ver)

    old_major = old_parts[0] if len(old_parts) > 0 else 0
    new_major = new_parts[0] if len(new_parts) > 0 else 0

    if new_major > old_major:
        return True

    # In 0.x semver (e.g. LangChain 0.1 -> 0.2), minor bumps are breaking
    if old_major == 0 and new_major == 0:
        old_minor = old_parts[1] if len(old_parts) > 1 else 0
        new_minor = new_parts[1] if len(new_parts) > 1 else 0
        if new_minor > old_minor:
            return True

    return False


def scan_diff_for_dependency_changes(parsed_diff: ParsedPRDiff) -> List[DependencyChange]:
    """Inspect unified diff of manifest files and detect upgraded dependencies."""
    changes: List[DependencyChange] = []
    manifest_files = parsed_diff.get_manifest_diffs()

    for file_diff in manifest_files:
        filename = file_diff.path
        removed_packages: dict[str, str] = {}
        added_packages: dict[str, str] = {}

        for rem in file_diff.get_removed_lines():
            res = extract_package_version_from_line(rem, filename)
            if res:
                removed_packages[res[0]] = res[1]

        for add in file_diff.get_added_lines():
            res = extract_package_version_from_line(add, filename)
            if res:
                added_packages[res[0]] = res[1]

        # Match packages present in both removed and added
        for pkg, new_ver in added_packages.items():
            if pkg in removed_packages:
                old_ver = removed_packages[pkg]
                if old_ver != new_ver:
                    changes.append(
                        DependencyChange(
                            package_name=pkg,
                            old_version=old_ver,
                            new_version=new_ver,
                            manifest_file=filename,
                            is_major_bump=is_major_or_breaking_bump(old_ver, new_ver),
                            details=f"Upgraded from {old_ver} to {new_ver} in {filename}",
                        )
                    )

    return changes
