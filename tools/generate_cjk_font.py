#!/usr/bin/env python3
"""Generate the fixed-cell CJK font tables used by Retro-Go.

The source font is Noto Sans CJK SC from the immutable URL recorded in
``FONT_SOURCE_URL`` below.

Pillow is needed only to regenerate the checked-in include files. Codepoint
selection and include validation work with the Python standard library alone.
"""

import argparse
import ast
import hashlib
import re
from functools import lru_cache
from pathlib import Path


GLYPH_WIDTH = 12
GLYPH_HEIGHT = 12
GLYPH_BYTES = GLYPH_WIDTH * GLYPH_HEIGHT // 8
PIXEL_THRESHOLD = 64

FONT_SOURCE_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-cjk/"
    "f8d157532fbfaeda587e826d4cd5b21a49186f7c/"
    "Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
)
FONT_SOURCE_FILENAME = "NotoSansCJKsc-Regular.otf"
EXPECTED_FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
DEFAULT_FONT_NAME = "Noto Sans CJK SC Regular"
COMMON_FILENAME_PUNCTUATION = (
    "，。！？；：、（）［］【】《》〈〉“”‘’「」『』·—…￥～"
)

_C_STRING = r'"(?:\\.|[^"\\])*"'
_C_TOKEN_RE = re.compile(
    r"//.*?$|/\*.*?\*/|" + _C_STRING + r"|'(?:\\.|[^'\\])*'",
    re.MULTILINE | re.DOTALL,
)
_ZH_INITIALIZER_RE = re.compile(
    r"\[\s*RG_LANG_ZH_CN\s*\]\s*=\s*"
    r"(?P<value>(?:" + _C_STRING + r"\s*)+),"
)


def _strip_c_comments(source):
    def replace(match):
        token = match.group(0)
        if not token.startswith("/"):
            return token
        return "".join("\n" if character == "\n" else " " for character in token)

    return _C_TOKEN_RE.sub(replace, source)


def _decode_c_strings(expression):
    return "".join(
        ast.literal_eval(match.group(0))
        for match in re.finditer(_C_STRING, expression)
    )


def _splice_c_lines(source):
    return re.sub(r"\\\r?\n", "", source)


def extract_menu_codepoints(source):
    """Return sorted non-Latin BMP codepoints from Chinese C initializers."""

    source = _splice_c_lines(source)
    source = _strip_c_comments(source)
    characters = set()
    for match in _ZH_INITIALIZER_RE.finditer(source):
        for character in _decode_c_strings(match.group("value")):
            codepoint = ord(character)
            if 0x0100 <= codepoint <= 0xFFFF:
                characters.add(codepoint)
    return sorted(characters)


@lru_cache(maxsize=1)
def _gb2312_han_codepoints():
    codepoints = []
    for codepoint in range(0x4E00, 0xA000):
        try:
            chr(codepoint).encode("gb2312")
        except UnicodeEncodeError:
            continue
        codepoints.append(codepoint)
    return tuple(codepoints)


def build_gb2312_codepoints(menu_codepoints=()):
    """Return GB2312 Han, filename punctuation, and supplied menu glyphs."""

    codepoints = set(_gb2312_han_codepoints())
    codepoints.update(ord(character) for character in COMMON_FILENAME_PUNCTUATION)
    for codepoint in menu_codepoints:
        if not 0x0100 <= codepoint <= 0xFFFF:
            raise ValueError(f"CJK codepoint does not fit uint16_t: U+{codepoint:04X}")
        codepoints.add(codepoint)
    return sorted(codepoints)


def rasterize_glyph(font, codepoint):
    """Rasterize one codepoint into a row-major, MSB-first 12x12 bitmap."""

    if not 0 <= codepoint <= 0xFFFF:
        raise ValueError(f"CJK codepoint does not fit uint16_t: U+{codepoint:04X}")

    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError(
            "Pillow is required to regenerate the CJK font assets"
        ) from error

    image = Image.new("L", (GLYPH_WIDTH, GLYPH_HEIGHT), 0)
    draw = ImageDraw.Draw(image)

    # Use one ideographic origin for every glyph. This keeps commas and periods
    # on the baseline while fitting Noto's square ideographs into the cell.
    reference_box = font.getbbox("田")
    origin_x = -reference_box[0]
    origin_y = -reference_box[1]
    draw.text((origin_x, origin_y), chr(codepoint), font=font, fill=255)

    packed = bytearray()
    byte = 0
    bits = 0
    for y in range(GLYPH_HEIGHT):
        for x in range(GLYPH_WIDTH):
            byte = (byte << 1) | (image.getpixel((x, y)) >= PIXEL_THRESHOLD)
            bits += 1
            if bits == 8:
                packed.append(byte)
                byte = 0
                bits = 0

    if bits:
        packed.append(byte << (8 - bits))
    if len(packed) != GLYPH_BYTES:
        raise AssertionError("12x12 glyph did not pack to exactly 18 bytes")
    return bytes(packed)


def _validate_font_data(codepoints, bitmaps, font_sha256):
    codepoints = list(codepoints)
    bitmaps = list(bitmaps)
    if not codepoints:
        raise ValueError("at least one codepoint is required")
    if codepoints != sorted(set(codepoints)):
        raise ValueError("codepoints must be sorted and unique")
    if any(not 0 <= codepoint <= 0xFFFF for codepoint in codepoints):
        raise ValueError("all codepoints must fit uint16_t")
    if len(bitmaps) != len(codepoints):
        raise ValueError("each codepoint must have exactly one bitmap")

    normalized_bitmaps = []
    for bitmap in bitmaps:
        try:
            values = list(bitmap)
        except TypeError as error:
            raise ValueError(
                "bitmap values must be integers from 0 through 255"
            ) from error
        if any(type(value) is not int or not 0 <= value <= 0xFF for value in values):
            raise ValueError("bitmap values must be integers from 0 through 255")
        normalized_bitmaps.append(bytes(values))
    bitmaps = normalized_bitmaps

    if any(len(bitmap) != GLYPH_BYTES for bitmap in bitmaps):
        raise ValueError(f"each bitmap must contain exactly {GLYPH_BYTES} bytes")
    if re.fullmatch(r"[0-9a-fA-F]{64}", font_sha256) is None:
        raise ValueError("font_sha256 must contain 64 hexadecimal characters")
    return codepoints, bitmaps


def write_include(
    output_path,
    codepoints,
    bitmaps,
    font_sha256,
    font_name=DEFAULT_FONT_NAME,
):
    """Write deterministic C arrays with symbols shared by both font sets."""

    codepoints, bitmaps = _validate_font_data(codepoints, bitmaps, font_sha256)
    lines = [
        "/* Generated by tools/generate_cjk_font.py. Do not edit. */",
        f"/* Font: {font_name} */",
        f"/* Font source: {FONT_SOURCE_URL} */",
        f"/* Font source file: {FONT_SOURCE_FILENAME} */",
        f"/* Font SHA-256: {font_sha256.lower()} */",
        "/* License: SIL Open Font License 1.1 (NotoSansCJK-OFL.txt) */",
        f"/* Glyphs: {len(codepoints)}; cell: {GLYPH_WIDTH}x{GLYPH_HEIGHT}; packed bytes: {GLYPH_BYTES} */",
        "",
        "static const uint16_t cjk_codepoints[] = {",
    ]

    for start in range(0, len(codepoints), 12):
        chunk = codepoints[start : start + 12]
        lines.append("    " + ", ".join(f"0x{value:04X}" for value in chunk) + ",")
    lines.extend(["};", "", f"static const uint8_t cjk_bitmaps[][{GLYPH_BYTES}] = {{"])

    for codepoint, bitmap in zip(codepoints, bitmaps):
        values = ", ".join(f"0x{value:02X}" for value in bitmap)
        lines.append(f"    /* U+{codepoint:04X} */ {{{values}}},")
    lines.extend(["};", ""])

    with Path(output_path).open("w", encoding="ascii", newline="\n") as output:
        output.write("\n".join(lines))


def _font_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rasterize_set(font, codepoints):
    bitmaps = []
    missing_bitmap = rasterize_glyph(font, 0xFFFF)
    for codepoint in codepoints:
        bitmap = rasterize_glyph(font, codepoint)
        if not any(bitmap):
            raise ValueError(f"font produced a blank glyph for U+{codepoint:04X}")
        if bitmap == missing_bitmap:
            raise ValueError(f"font is missing glyph U+{codepoint:04X}")
        bitmaps.append(bitmap)
    return bitmaps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--menu-output", required=True, type=Path)
    parser.add_argument("--full-output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        from PIL import ImageFont
    except ImportError as error:
        parser.error(f"Pillow is required to regenerate the font assets: {error}")

    source = args.translations.read_text(encoding="utf-8")
    menu_codepoints = extract_menu_codepoints(source)
    full_codepoints = build_gb2312_codepoints(menu_codepoints)
    font_sha256 = _font_sha256(args.font)
    font = ImageFont.truetype(str(args.font), GLYPH_HEIGHT)
    font_name = " ".join(font.getname())
    if font_name != DEFAULT_FONT_NAME or font_sha256 != EXPECTED_FONT_SHA256:
        raise ValueError(
            f"font must be {DEFAULT_FONT_NAME} with SHA-256 "
            f"{EXPECTED_FONT_SHA256}"
        )

    write_include(
        args.menu_output,
        menu_codepoints,
        _rasterize_set(font, menu_codepoints),
        font_sha256,
        font_name,
    )
    write_include(
        args.full_output,
        full_codepoints,
        _rasterize_set(font, full_codepoints),
        font_sha256,
        font_name,
    )

    print(f"menu glyphs: {len(menu_codepoints)} -> {args.menu_output}")
    print(f"full glyphs: {len(full_codepoints)} -> {args.full_output}")
    print(f"font SHA-256: {font_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
