#!/usr/bin/env python3
"""Check release source syntax, links, and common credential patterns."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


IGNORED_DIRS = {
    ".agents", ".aws", ".codex", ".git", ".local-research", ".runtime", ".venv",
    "__pycache__", "build", "captures", "data", "deployment", "generated",
    "identity-data", "logs", "secure", "cardano-static",
}
PRIVATE_SUFFIXES = {".key", ".pem", ".p12", ".skey", ".signed", ".txbody", ".pcap", ".pcapng"}
CREDENTIAL = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r'|"type"\s*:\s*"[^"\n]*SigningKey[^"\n]*"'
    r"|(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16})"
    r"""|(?im:(?:^|\s)(?:password|passwd|api_key|access_token|client_secret)\s*=\s*["'][^"'\n]{8,}["'])"""
)
LINK = re.compile(r"\]\(([^\s)]+)\)")


def main():
    root = Path(__file__).resolve().parent.parent
    totals = dict(python=0, json=0, shell=0, markdown=0)
    issues = []

    for directory, folders, files in os.walk(root):
        folders[:] = sorted(
            folder for folder in folders
            if folder not in IGNORED_DIRS and not folder.startswith("output")
        )
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if (relative.as_posix() == "experiments/B11-cardano/resources/cardano-static"
                    and path.is_symlink()
                    and os.readlink(path) == "../../../resources/cardano/11.0.1"):
                continue
            if path.is_symlink() or path.suffix in PRIVATE_SUFFIXES or name.startswith(".env"):
                issues.append(f"{relative}: excluded artifact or symlink")
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    issues.append(f"{relative}: file exceeds release review size")
                    continue
                content = path.read_text()
                if CREDENTIAL.search(content):
                    issues.append(f"{relative}: potential credential pattern")
                if path.suffix == ".py":
                    compile(content, str(relative), "exec")
                    totals["python"] += 1
                elif path.suffix == ".json":
                    json.loads(content)
                    totals["json"] += 1
                elif path.suffix == ".sh":
                    subprocess.run(["bash", "-n", str(path)], check=True)
                    totals["shell"] += 1
                elif path.suffix == ".md":
                    for link in LINK.findall(content):
                        target = link.split("#", 1)[0]
                        if target and "://" not in target and not (path.parent / target).exists():
                            issues.append(f"{relative}: missing link target {target}")
                    totals["markdown"] += 1
            except (SyntaxError, ValueError, OSError, subprocess.CalledProcessError) as error:
                issues.append(f"{relative}: {type(error).__name__}")

    print(", ".join(f"{count} {kind}" for kind, count in totals.items()))
    for issue in issues:
        print(issue, file=sys.stderr)
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
