"""Check for a stable renderer release and optionally prepare its update."""

import argparse
import os
import re
import subprocess
from pathlib import Path

import tomllib

STABLE_TAG = re.compile(r"refs/tags/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
CRATES = ("osu-beatmap-preview-core", "osu-beatmap-preview-cli")


def prepare_update(root: Path, repository: str, current: str, revision: str, tag: str) -> None:
    git = ["git", "-C", str(root)]
    remote_ref = "refs/upstream-check/latest"
    subprocess.run(
        [
            *git,
            "fetch",
            "--no-tags",
            "--depth=1",
            repository,
            revision,
            f"+refs/tags/{tag}:{remote_ref}",
        ],
        check=True,
        timeout=180,
    )
    latest = subprocess.check_output(
        [*git, "rev-parse", f"{remote_ref}^{{commit}}"], text=True
    ).strip()
    diff = subprocess.check_output(
        [
            *git,
            "diff",
            "--binary",
            "--relative=crates",
            revision,
            latest,
            "--",
            *(f"crates/{crate}" for crate in CRATES),
        ],
    )
    if diff:
        subprocess.run([*git, "apply", "--directory=vendor"], input=diff, check=True)

    paths = [root / name for name in ("Cargo.toml", "README.md", "THIRD_PARTY_NOTICES.md")]
    paths.extend(
        root / "vendor" / crate / name
        for crate in CRATES
        for name in ("Cargo.toml", "UPSTREAM.toml")
    )
    for path in paths:
        original = path.read_text(encoding="utf-8")
        updated = (
            original.replace(revision, latest)
            .replace(f"`{revision[:7]}`", f"`{latest[:7]}`")
            .replace(f"v{current}", tag, 1)
            .replace(f'version = "{current}"', f'version = "{tag[1:]}"')
        )
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifests = [
        tomllib.loads((root / "vendor" / crate / "UPSTREAM.toml").read_text(encoding="utf-8"))
        for crate in CRATES
    ]
    core, cli = manifests
    for field in ("repository", "version", "revision"):
        if core[field] != cli[field]:
            raise SystemExit(f"Core and CLI upstream {field} differ.")

    repository = core["repository"]
    current = tuple(map(int, core["version"].split(".")))
    remote = subprocess.run(
        ["git", "ls-remote", "--refs", "--tags", repository, "v*"],
        stdout=subprocess.PIPE,
        check=True,
        text=True,
        timeout=45,
    )
    versions = [
        tuple(map(int, match.groups()))
        for line in remote.stdout.splitlines()
        if (match := STABLE_TAG.fullmatch(line.split("\t", 1)[1]))
    ]
    if not versions:
        raise SystemExit("No stable upstream version tags found.")

    latest = max(versions)
    tag = "v" + ".".join(map(str, latest))
    message = f"固定版本 v{core['version']}，上游最新稳定版本 {tag}。"
    if latest > current:
        message += " 发现上游更新。"
        if os.getenv("GITHUB_ACTIONS") == "true":
            print(f"::notice title=Upstream update::{message}")
    print(message)

    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"{message}\n\n[查看上游标签]({repository}/tree/{tag})\n")

    if latest > current and args.prepare:
        prepare_update(root, repository, core["version"], core["revision"], tag)
        if output := os.getenv("GITHUB_OUTPUT"):
            with Path(output).open("a", encoding="utf-8") as stream:
                stream.write(f"tag={tag}\ncurrent=v{core['version']}\nrepository={repository}\n")


if __name__ == "__main__":
    main()
