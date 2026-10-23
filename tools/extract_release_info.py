#!/usr/bin/env python3
"""
extract_release_info.py

Extracts version information from build.ctl/gateway.asm and the latest entry
from CHANGELOG.html to prepare release notes and metadata for GitHub Releases.
"""

import os
import sys
import re
import html


def parse_build_ctl(ctl_path="build.ctl"):
    config = {}
    if os.path.exists(ctl_path):
        with open(ctl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    config[parts[0]] = parts[1]
    return config


def parse_gateway_asm(asm_path="gateway.asm"):
    defines = {}
    if os.path.exists(asm_path):
        with open(asm_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = re.sub(r";.*$", "", line).strip()
                m = re.match(r"#define\s+(\S+)\s+(.+)", line)
                if m:
                    name, val = m.group(1), m.group(2).strip().strip('"')
                    defines[name] = val
    return defines


def get_version_info():
    ctl = parse_build_ctl()
    asm = parse_gateway_asm()

    version = ctl.get("version") or asm.get("version") or "1.0"
    phase = ctl.get("phase") or asm.get("phase") or "."
    patch = ctl.get("patch") or asm.get("patch") or "0"
    bugfix = ctl.get("bugfix") or asm.get("bugfix") or "0"

    phase_map = {
        "a": "alpha",
        "b": "beta",
        "rc": "rc",
    }
    phase_clean = phase_map.get(phase, "" if phase == "." else phase)
    is_prerelease = bool(phase_clean)

    suffix = ""
    if phase_clean:
        suffix = f"-{phase_clean}"
        if patch and patch != "0":
            suffix += f".{patch}"
    else:
        if bugfix and bugfix != "0":
            suffix += f".{bugfix}"

    tag = f"v{version}{suffix}"
    return {
        "version": version,
        "phase": phase,
        "patch": patch,
        "bugfix": bugfix,
        "tag": tag,
        "prerelease": "true" if is_prerelease else "false",
    }


def extract_changelog(changelog_path="CHANGELOG.html"):
    if not os.path.exists(changelog_path):
        return None, ""

    with open(changelog_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Find the first <h3> header and everything until next <h3> or end of content
    match = re.search(
        r"(?s)<h3>(.*?)</h3>(.*?)(?=<h3>|<table|<td id=\"content\"|</body>|$)",
        content,
    )
    if not match:
        return None, ""

    raw_title = match.group(1)
    title = (
        html.unescape(raw_title)
        .replace("&mdash;", "—")
        .replace("&ndash;", "–")
        .strip()
    )
    title = re.sub(r"\s+", " ", title)

    section = match.group(2)
    lines = []

    tokens = re.finditer(r"(?s)(?:<b>(.*?)</b>|<li>(.*?)</li>)", section)
    for tok in tokens:
        if tok.group(1) is not None:
            subhead = html.unescape(tok.group(1)).strip()
            subhead = re.sub(r"\s+", " ", subhead)
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"**{subhead}**")
        elif tok.group(2) is not None:
            item_raw = tok.group(2)
            # Convert <a href="url">text</a> to [text](url)
            item_md = re.sub(
                r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                r"[\2](\1)",
                item_raw,
            )
            # Remove any remaining HTML tags
            item_clean = re.sub(r"<[^>]+>", "", item_md)
            # Unescape entities
            item_clean = html.unescape(item_clean)
            # Normalize whitespace
            item_clean = re.sub(r"\s+", " ", item_clean).strip()
            if item_clean:
                lines.append(f"- {item_clean}")

    body = "\n".join(lines).strip()
    return title, body


def main():
    info = get_version_info()
    title, body = extract_changelog()

    # If triggered via a Git tag, override tag name with GITHUB_REF_NAME if available
    ref_type = os.environ.get("GITHUB_REF_TYPE", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")
    if ref_type == "tag" and ref_name:
        tag = ref_name
    else:
        tag = info["tag"]

    release_title = title if title else f"Release {tag}"
    prerelease = info["prerelease"]

    # Compose release notes markdown
    notes = []
    notes.append(f"### {release_title}\n")
    if body:
        notes.append(body)
    else:
        notes.append("See commit log for details.")

    notes_content = "\n".join(notes).strip() + "\n"

    with open("release_notes.md", "w", encoding="utf-8") as f:
        f.write(notes_content)

    print(f"Tag: {tag}")
    print(f"Title: {release_title}")
    print(f"Prerelease: {prerelease}")
    print("Release notes written to release_notes.md")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"tag={tag}\n")
            f.write(f"title={release_title}\n")
            f.write(f"prerelease={prerelease}\n")


if __name__ == "__main__":
    main()

