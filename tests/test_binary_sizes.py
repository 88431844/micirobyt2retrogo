import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tests" / "check_binary_sizes.py"
PACKAGER = ROOT / "tools" / "mkfw.py"
LIMITS = {
    "launcher": 2097152,
    "retro-core": 2097152,
    "prboom-go": 1048576,
    "gwenesis": 1572864,
    "fmsx": 1048576,
}


class BinarySizeCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_binary(self, app, size):
        path = self.repo_root / app / "build" / f"{app}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as output:
            output.truncate(size)
        return path

    def run_checker(self):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.repo_root)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_each_packaged_application_binary_at_its_limit(self):
        for app, limit in LIMITS.items():
            self.write_binary(app, limit)

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)
        for app, limit in LIMITS.items():
            self.assertIn(f"OK: {app}: {limit} / {limit} bytes", result.stdout)
        self.assertIn("All 5 application binaries fit", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_fails_clearly_when_a_required_binary_is_missing(self):
        for app in LIMITS:
            if app != "fmsx":
                self.write_binary(app, 1)

        result = self.run_checker()

        expected_path = self.repo_root / "fmsx" / "build" / "fmsx.bin"
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR: fmsx: missing binary", result.stderr)
        self.assertIn(str(expected_path), result.stderr)
        self.assertIn("Binary size check failed with 1 error", result.stderr)

    def test_fails_clearly_when_each_binary_exceeds_its_limit(self):
        for app, limit in LIMITS.items():
            self.write_binary(app, limit)

        for app, limit in LIMITS.items():
            with self.subTest(app=app):
                self.write_binary(app, limit + 1)

                result = self.run_checker()

                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"ERROR: {app}: {limit + 1} bytes exceeds "
                    f"{limit}-byte limit by 1 byte",
                    result.stderr,
                )
                self.assertIn("Binary size check failed with 1 error", result.stderr)
                self.write_binary(app, limit)


class FirmwarePackagerSizeTests(unittest.TestCase):
    def test_packager_rejects_a_binary_larger_than_its_partition(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "launcher.bin"
            output = root / "firmware.fw"
            binary.write_bytes(b"AB")

            result = subprocess.run(
                [
                    sys.executable,
                    str(PACKAGER),
                    "--type",
                    "odroid",
                    "--icon",
                    "none",
                    str(output),
                    "0",
                    "16",
                    "1",
                    "launcher",
                    str(binary),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("launcher.bin", result.stderr)
            self.assertIn("exceeds its 1-byte partition", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
