import contextlib
import hashlib
import io
import re
import tempfile
import unittest
from pathlib import Path

from tools.generate_cjk_font import (
    FONT_SOURCE_URL,
    GLYPH_BYTES,
    _rasterize_set,
    build_gb2312_codepoints,
    extract_menu_codepoints,
    main,
    rasterize_glyph,
    write_include,
)


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "components" / "retro-go" / "fonts"
TRANSLATIONS = ROOT / "components" / "retro-go" / "translations.h"
MENU_INCLUDE = FONTS / "cjk_menu_data.inc"
FULL_INCLUDE = FONTS / "cjk_gb2312_data.inc"
TEST_FONT = ROOT / "tools" / "fonts" / "DejaVuSans.ttf"
NOTO_FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
NOTO_LICENSE_SHA256 = "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9"

CODEPOINT_ARRAY_RE = re.compile(
    r"static const uint16_t cjk_codepoints\[\]\s*=\s*\{(?P<body>.*?)\};",
    re.DOTALL,
)
BITMAP_ARRAY_RE = re.compile(
    r"static const uint8_t cjk_bitmaps\[\]\[18\]\s*=\s*\{(?P<body>.*?)\};",
    re.DOTALL,
)
C_COMMENT_RE = re.compile(r"//[^\r\n]*(?:\r?\n|$)|/\*.*?\*/", re.DOTALL)


def strip_include_comments(source):
    source = re.sub(r"\\\r?\n", "", source)
    return C_COMMENT_RE.sub(
        lambda match: "".join(
            "\n" if character == "\n" else " " for character in match.group(0)
        ),
        source,
    )


def parse_hex_tokens(body, digits):
    token_re = re.compile(
        rf"\s*0x(?P<value>[0-9A-Fa-f]{{{digits}}})(?:\s*,|\s*$)"
    )
    values = []
    position = 0
    while body[position:].strip():
        match = token_re.match(body, position)
        if match is None:
            raise AssertionError("invalid generated include token")
        values.append(int(match.group("value"), 16))
        position = match.end()
    return values


def parse_bitmap_rows(body):
    row_re = re.compile(r"\s*\{(?P<body>[^{}]*)\}\s*,")
    bitmaps = []
    position = 0
    while body[position:].strip():
        match = row_re.match(body, position)
        if match is None:
            raise AssertionError("invalid generated include bitmap row")
        bitmaps.append(bytes(parse_hex_tokens(match.group("body"), 2)))
        position = match.end()
    return bitmaps


def parse_include(path):
    source = path.read_text(encoding="ascii")
    uncommented = strip_include_comments(source)
    codepoint_matches = list(CODEPOINT_ARRAY_RE.finditer(uncommented))
    bitmap_matches = list(BITMAP_ARRAY_RE.finditer(uncommented))
    if len(codepoint_matches) != 1 or len(bitmap_matches) != 1:
        raise AssertionError(f"invalid generated include arrays in {path}")

    codepoints = parse_hex_tokens(codepoint_matches[0].group("body"), 4)
    bitmaps = parse_bitmap_rows(bitmap_matches[0].group("body"))
    return source, codepoints, bitmaps


class IncludeParserTests(unittest.TestCase):
    def test_parser_ignores_hex_tokens_inside_c_comments(self):
        bitmap = ", ".join(f"0x{value:02X}" for value in range(GLYPH_BYTES))
        source = f"""
/* Metadata that is not data: 0xCAFE. */
static const uint16_t cjk_codepoints[] = {{
    /* Decoy: 0x1234. */ 0x4E2D,
}};
static const uint8_t cjk_bitmaps[][18] = {{
    /* U+4E2D; decoy byte: 0xEE. */ {{{bitmap}}},
}};
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            include = Path(temp_dir) / "synthetic.inc"
            include.write_text(source, encoding="ascii")

            _, codepoints, bitmaps = parse_include(include)

        self.assertEqual(codepoints, [ord("中")])
        self.assertEqual(bitmaps, [bytes(range(GLYPH_BYTES))])

    def test_parser_rejects_noncanonical_hex_tokens_without_truncating(self):
        valid_bitmap = ", ".join(["0x00"] * GLYPH_BYTES)
        cases = (
            ("short codepoint", "0x100", valid_bitmap),
            (
                "oversized bitmap byte",
                "0x4E2D",
                ", ".join(["0x100"] + ["0x00"] * (GLYPH_BYTES - 1)),
            ),
        )
        for label, codepoint, bitmap in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                include = Path(temp_dir) / "malformed.inc"
                include.write_text(
                    f"""
static const uint16_t cjk_codepoints[] = {{{codepoint},}};
static const uint8_t cjk_bitmaps[][18] = {{{{{bitmap}}},}};
""",
                    encoding="ascii",
                )

                with self.assertRaisesRegex(AssertionError, "invalid generated include"):
                    parse_include(include)


class CodepointSetTests(unittest.TestCase):
    def test_menu_codepoints_come_from_chinese_c_string_literals(self):
        source = r'''
static const char *language_names[RG_LANG_MAX] = {
    [RG_LANG_EN] = "Chinese text must not be selected",
    [RG_LANG_ZH_CN] = "简体" "中文",
};
static const char *translations[][RG_LANG_MAX] = {
    {
        [RG_LANG_EN] = "Game",
        [RG_LANG_ZH_CN] = "游" "戏！",
    },
};
'''

        self.assertEqual(
            extract_menu_codepoints(source),
            sorted({ord(character) for character in "简体中文游戏！"}),
        )

    def test_menu_extraction_applies_c_line_splicing_inside_literals(self):
        line_splice = "\\" + "\n"
        source = '[RG_LANG_ZH_CN] = "中' + line_splice + '文",\n'

        self.assertEqual(
            extract_menu_codepoints(source),
            [ord("中"), ord("文")],
        )

    def test_line_spliced_comment_continuation_cannot_inject_initializer(self):
        line_splice = "\\" + "\n"
        source = (
            "// decoy continues" + line_splice
            + '[RG_LANG_ZH_CN] = "错误",\n'
            + '[RG_LANG_ZH_CN] = "中",\n'
        )

        self.assertEqual(extract_menu_codepoints(source), [ord("中")])

    def test_gb2312_han_contains_representative_characters(self):
        codepoints = build_gb2312_codepoints()

        for character in "中文游戏":
            self.assertIn(ord(character), codepoints)

    def test_gb2312_codepoints_are_sorted_and_unique(self):
        codepoints = build_gb2312_codepoints(
            [ord("界"), ord("？"), ord("中"), ord("界")]
        )

        self.assertEqual(codepoints, sorted(set(codepoints)))
        self.assertTrue({ord("界"), ord("？")} <= set(codepoints))


class RasterizationTests(unittest.TestCase):
    @unittest.skipUnless(TEST_FONT.exists(), "repository test font is unavailable")
    def test_rasterized_bitmap_is_12_by_12_and_nonblank(self):
        try:
            from PIL import ImageFont
        except ImportError:
            self.skipTest("Pillow is only required when regenerating font assets")

        font = ImageFont.truetype(str(TEST_FONT), 12)
        bitmap = rasterize_glyph(font, ord("A"))

        self.assertEqual(len(bitmap), GLYPH_BYTES)
        self.assertNotEqual(bitmap, bytes(GLYPH_BYTES))

    @unittest.skipUnless(TEST_FONT.exists(), "repository test font is unavailable")
    def test_repeated_rasterization_and_include_generation_is_byte_identical(self):
        try:
            from PIL import ImageFont
        except ImportError:
            self.skipTest("Pillow is only required when regenerating font assets")

        font = ImageFont.truetype(str(TEST_FONT), 12)
        codepoints = [ord("A"), ord("B")]
        font_sha256 = hashlib.sha256(TEST_FONT.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = [Path(temp_dir) / name for name in ("first.inc", "second.inc")]
            for output in outputs:
                bitmaps = [rasterize_glyph(font, codepoint) for codepoint in codepoints]
                write_include(output, codepoints, bitmaps, font_sha256)

            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())

    @unittest.skipUnless(TEST_FONT.exists(), "repository test font is unavailable")
    def test_rasterize_set_rejects_dejavu_notdef_for_chinese(self):
        try:
            from PIL import ImageFont
        except ImportError:
            self.skipTest("Pillow is only required when regenerating font assets")

        font = ImageFont.truetype(str(TEST_FONT), 12)

        with self.assertRaisesRegex(ValueError, r"missing glyph U\+4E2D"):
            _rasterize_set(font, [ord("中")])


class CommandLineTests(unittest.TestCase):
    @unittest.skipUnless(TEST_FONT.exists(), "repository test font is unavailable")
    def test_cli_rejects_a_font_with_the_wrong_identity(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow is only required when regenerating font assets")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            translations = temp_dir / "translations.h"
            translations.write_text(
                '[RG_LANG_ZH_CN] = "中",\n', encoding="utf-8"
            )
            arguments = [
                "--font",
                str(TEST_FONT),
                "--translations",
                str(translations),
                "--menu-output",
                str(temp_dir / "menu.inc"),
                "--full-output",
                str(temp_dir / "full.inc"),
            ]

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "Noto Sans CJK SC"):
                    main(arguments)


class IncludeWriterTests(unittest.TestCase):
    def test_repeated_include_serialization_is_byte_identical(self):
        codepoints = [ord("中"), ord("文")]
        bitmaps = [bytes([0xAA]) * GLYPH_BYTES, bytes([0x55]) * GLYPH_BYTES]
        font_sha256 = hashlib.sha256(b"test font").hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.inc"
            second = Path(temp_dir) / "second.inc"
            write_include(first, codepoints, bitmaps, font_sha256)
            write_include(second, codepoints, bitmaps, font_sha256)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertIn(font_sha256.encode("ascii"), first.read_bytes())
            self.assertIn(b"NotoSansCJKsc-Regular.otf", first.read_bytes())

    def test_bitmap_values_are_normalized_to_bytes(self):
        codepoints = [ord("中")]
        bitmap = bytearray(range(GLYPH_BYTES))
        font_sha256 = hashlib.sha256(b"test font").hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "normalized.inc"
            write_include(output, codepoints, [bitmap], font_sha256)
            _, _, bitmaps = parse_include(output)

        self.assertEqual(bitmaps, [bytes(range(GLYPH_BYTES))])

    def test_bitmap_values_must_be_byte_sized_integers(self):
        font_sha256 = hashlib.sha256(b"test font").hexdigest()
        invalid_bitmaps = (
            [256] + [0] * (GLYPH_BYTES - 1),
            [-1] + [0] * (GLYPH_BYTES - 1),
            [1.5] + [0] * (GLYPH_BYTES - 1),
        )
        for bitmap in invalid_bitmaps:
            with self.subTest(first_value=bitmap[0]), tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "invalid.inc"

                with self.assertRaisesRegex(
                    ValueError, "bitmap values must be integers from 0 through 255"
                ):
                    write_include(output, [ord("中")], [bitmap], font_sha256)


class CheckedInAssetTests(unittest.TestCase):
    def test_checked_in_assets_record_exact_noto_metadata_and_license(self):
        expected_comments = (
            "/* Font: Noto Sans CJK SC Regular */",
            f"/* Font source: {FONT_SOURCE_URL} */",
            "/* Font source file: NotoSansCJKsc-Regular.otf */",
            f"/* Font SHA-256: {NOTO_FONT_SHA256} */",
            "/* License: SIL Open Font License 1.1 (NotoSansCJK-OFL.txt) */",
        )
        for path in (MENU_INCLUDE, FULL_INCLUDE):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="ascii")
                for comment in expected_comments:
                    self.assertIn(comment, source)

        license_data = (FONTS / "NotoSansCJK-OFL.txt").read_bytes()
        self.assertEqual(hashlib.sha256(license_data).hexdigest(), NOTO_LICENSE_SHA256)
        license_text = license_data.decode("ascii")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)
        self.assertIn("Reserved Font Name 'Source'", license_text)

    def test_menu_asset_exactly_covers_current_chinese_catalog(self):
        _, codepoints, bitmaps = parse_include(MENU_INCLUDE)

        self.assertEqual(
            codepoints,
            extract_menu_codepoints(TRANSLATIONS.read_text(encoding="utf-8")),
        )
        self.assertEqual(len(bitmaps), len(codepoints))

    def test_full_asset_covers_gb2312_and_all_menu_codepoints(self):
        _, menu_codepoints, _ = parse_include(MENU_INCLUDE)
        _, full_codepoints, bitmaps = parse_include(FULL_INCLUDE)

        self.assertEqual(full_codepoints, build_gb2312_codepoints(menu_codepoints))
        self.assertEqual(len(bitmaps), len(full_codepoints))

    def test_checked_in_codepoints_are_sorted_unique_and_bmp(self):
        for path in (MENU_INCLUDE, FULL_INCLUDE):
            with self.subTest(path=path.name):
                _, codepoints, _ = parse_include(path)
                self.assertEqual(codepoints, sorted(set(codepoints)))
                self.assertTrue(codepoints)
                self.assertLessEqual(codepoints[-1], 0xFFFF)

    def test_checked_in_glyphs_are_18_bytes_and_representatives_nonblank(self):
        for path, representatives in (
            (MENU_INCLUDE, "中文游戏"),
            (FULL_INCLUDE, "中文游戏，。！？《》"),
        ):
            with self.subTest(path=path.name):
                _, codepoints, bitmaps = parse_include(path)
                by_codepoint = dict(zip(codepoints, bitmaps))
                self.assertTrue(all(len(bitmap) == GLYPH_BYTES for bitmap in bitmaps))
                for character in representatives:
                    self.assertIn(ord(character), by_codepoint)
                    self.assertNotEqual(by_codepoint[ord(character)], bytes(GLYPH_BYTES))


if __name__ == "__main__":
    unittest.main()
