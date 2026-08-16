#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# These are the application partition sizes passed to tools/mkfw.py by
# rg_tool.py. The packager warns and expands an overflowing partition, so the
# release check must reject that case before an image is flashed.
APP_LIMITS = {
    "launcher": 2097152,
    "retro-core": 2097152,
    "prboom-go": 1048576,
    "gwenesis": 1572864,
    "fmsx": 1048576,
}


def binary_path(root, app):
    return root / app / "build" / f"{app}.bin"


def check_binary_sizes(root, stdout=sys.stdout, stderr=sys.stderr):
    errors = 0

    for app, limit in APP_LIMITS.items():
        path = binary_path(root, app)
        try:
            if not path.is_file():
                raise FileNotFoundError
            size = path.stat().st_size
        except FileNotFoundError:
            print(f"ERROR: {app}: missing binary: {path}", file=stderr)
            errors += 1
            continue
        except OSError as error:
            print(f"ERROR: {app}: cannot read binary {path}: {error}", file=stderr)
            errors += 1
            continue

        if size > limit:
            excess = size - limit
            suffix = "" if excess == 1 else "s"
            print(
                f"ERROR: {app}: {size} bytes exceeds {limit}-byte limit "
                f"by {excess} byte{suffix}: {path}",
                file=stderr,
            )
            errors += 1
        else:
            print(f"OK: {app}: {size} / {limit} bytes ({path})", file=stdout)

    if errors:
        suffix = "" if errors == 1 else "s"
        print(
            f"Binary size check failed with {errors} error{suffix}.",
            file=stderr,
        )
        return 1

    print(
        f"All {len(APP_LIMITS)} application binaries fit configured limits.",
        file=stdout,
    )
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Check Retro-Go application binaries against partition limits."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository/build-tree root (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return check_binary_sizes(args.root)


if __name__ == "__main__":
    sys.exit(main())
