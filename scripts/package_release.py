#!/usr/bin/env python3
"""Build a safe source archive and release notes for the AstrBot plugin."""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    ".gitignore", "scripts/package_release.py", ".github/workflows/release.yml",
    "metadata.yaml", "README.md", "CHANGELOG.md", "main.py", "_conf_schema.json",
    "tests/test_main.py",
)


def current_version() -> str:
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*['\"]?([0-9]+\.[0-9]+\.[0-9]+)['\"]?\s*$", metadata)
    if not match:
        raise SystemExit("metadata.yaml must define a three-part version")
    version = match.group(1)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest = re.search(r"(?m)^##\s+v?(\d+\.\d+\.\d+)", changelog)
    if not latest or latest.group(1) != version:
        raise SystemExit("CHANGELOG first release heading must match the current version")
    if not re.search(rf"(?m)^v{re.escape(version)}\s+—", readme):
        raise SystemExit(f"README current version does not match metadata.yaml version {version}")
    if not re.search(rf"(?m)^##\s+v?{re.escape(version)}\s*$", changelog):
        raise SystemExit(f"CHANGELOG latest version does not match metadata.yaml version {version}")
    return version


def add_file(archive: zipfile.ZipFile, source: Path, name: str) -> None:
    info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
    archive.writestr(info, source.read_bytes())


def latest_notes(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"(?m)^##\s+v?{re.escape(version)}\s*$", text)
    assert match is not None
    remainder = text[match.end():]
    next_heading = re.search(r"(?m)^##\s+", remainder)
    section = remainder[:next_heading.start()] if next_heading else remainder
    return f"# astrbot_plugin_random_geng v{version}\n\n{section.strip()}\n"


def main() -> None:
    if sys.argv[1:] == ["--version"]:
        print(current_version())
        return
    if sys.argv[1:]:
        raise SystemExit("usage: package_release.py [--version]")
    version = current_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive_path = dist / f"astrbot-plugin-random-geng-v{version}-source.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCE_FILES:
            source = ROOT / name
            if not source.is_file():
                raise SystemExit(f"Required release file is missing: {name}")
            add_file(archive, source, name)
    (dist / "release-notes.md").write_text(latest_notes(version), encoding="utf-8")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (dist / "SHA256SUMS").write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")


if __name__ == "__main__":
    main()
