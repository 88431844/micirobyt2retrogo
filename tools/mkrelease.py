#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("build/release")
TARGET_ROOT = Path("components/retro-go/targets")


def target_artifacts(target):
    return sorted(Path.cwd().glob(f"retro-go_*_{target}.*"))


def build_target(target):
    for artifact in target_artifacts(target):
        artifact.unlink()

    print(f"Building {target}")
    subprocess.run(
        [sys.executable, "rg_tool.py", f"--target={target}", "release"],
        check=True,
    )

    artifacts = target_artifacts(target)
    if not artifacts:
        raise RuntimeError(f"Release build for {target} produced no artifacts")
    for artifact in artifacts:
        shutil.move(str(artifact), OUTPUT_DIR / artifact.name)


def main():
    targets = sorted(path.name for path in TARGET_ROOT.iterdir() if path.is_dir())
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for target in targets:
        build_target(target)

    subprocess.run([sys.executable, "rg_tool.py", "clean"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
