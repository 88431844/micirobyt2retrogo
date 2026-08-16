import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "release_metadata.py"
README = ROOT / "README.md"
RG_TOOL = ROOT / "rg_tool.py"
GENERATOR = ROOT / "tools" / "generate_cjk_font.py"
RELEASE_DRIVER = ROOT / "tools" / "mkrelease.py"


def load_release_metadata():
    spec = importlib.util.spec_from_file_location("release_metadata", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseMetadataTests(unittest.TestCase):
    def test_release_driver_does_not_collect_stale_artifacts_after_a_failed_build(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "components/retro-go/targets/microbyte").mkdir(parents=True)
            (root / "rg_tool.py").write_text(
                "raise SystemExit(7)\n",
                encoding="ascii",
            )
            stale_files = (
                root / "retro-go_old_microbyte.img",
                root / "retro-go_old_microbyte.img.OFL.txt",
            )
            for path in stale_files:
                path.write_bytes(b"stale")

            result = subprocess.run(
                [sys.executable, str(RELEASE_DRIVER)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            for path in stale_files:
                self.assertFalse((root / "build/release" / path.name).exists())

    def test_firmware_license_sidecar_matches_the_checked_in_ofl(self):
        self.assertTrue(MODULE_PATH.is_file(), "release metadata helper is missing")
        metadata = load_release_metadata()

        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "retro-go_test_microbyte.img"
            artifact.write_bytes(b"firmware")

            sidecar = metadata.copy_font_license(artifact)

            self.assertEqual(sidecar.name, artifact.name + ".OFL.txt")
            self.assertEqual(sidecar.read_bytes(), metadata.FONT_LICENSE.read_bytes())

    def test_firmware_builder_always_emits_the_license_sidecar(self):
        source = RG_TOOL.read_text(encoding="utf-8")
        build_image = re.search(
            r"def build_image\b(?P<body>.*?)(?=\ndef \w|\Z)", source, re.DOTALL
        )
        self.assertIsNotNone(build_image)
        self.assertIn("copy_font_license(output_file)", build_image.group("body"))

    def test_readme_declares_the_noto_cjk_ofl_exception(self):
        source = README.read_text(encoding="utf-8")
        self.assertRegex(
            source,
            r"(?i)cjk.*Noto Sans CJK.*SIL Open Font License.*1\.1",
        )

    def test_font_source_url_is_pinned_to_an_immutable_commit(self):
        source = GENERATOR.read_text(encoding="utf-8")
        match = re.search(r'FONT_SOURCE_URL\s*=\s*\((?P<body>.*?)\)', source, re.DOTALL)
        self.assertIsNotNone(match)
        url = "".join(re.findall(r'"([^"]*)"', match.group("body")))
        self.assertRegex(url, r"/[0-9a-f]{40}/")
        self.assertNotIn("/main/", url)


if __name__ == "__main__":
    unittest.main()
