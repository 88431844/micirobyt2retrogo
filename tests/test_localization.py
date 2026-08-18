import ast
import re
import tempfile
import unittest
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETRO_GO = ROOT / "components" / "retro-go"
LOCALIZATION_HEADER = RETRO_GO / "rg_localization.h"
TRANSLATIONS_HEADER = RETRO_GO / "translations.h"
SHARED_CONFIG = RETRO_GO / "config.h"
MICROBYTE_CONFIG = RETRO_GO / "targets" / "microbyte" / "config.h"
MICROBYTE_SDKCONFIG = RETRO_GO / "targets" / "microbyte" / "sdkconfig"

CPP_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
STRING_TOKEN = r'"(?:\\.|[^"\\])*"'
COMMENT_OR_LITERAL_RE = re.compile(
    r"//.*?$|/\*.*?\*/|" + STRING_TOKEN + r"|'(?:\\.|[^'\\])*'",
    re.MULTILINE | re.DOTALL,
)
TRANSLATION_FIELD_RE = re.compile(
    r"\[(RG_LANG_[A-Z_]+)\]\s*=\s*((?:" + STRING_TOKEN + r"\s*)+),"
)
GETTEXT_LITERAL_RE = re.compile(
    r"(?<![A-Za-z0-9_])_\s*\(\s*(?P<value>(?:" + STRING_TOKEN + r"\s*)+)"
)
PRINTF_TOKEN_RE = re.compile(
    r"%(?:%|(?:[1-9]\d*\$)?[-+ #0']*(?:\d+|\*)?"
    r"(?:\.(?:\d+|\*))?(?:hh|h|ll|l|j|z|t|L)?"
    r"[diuoxXfFeEgGaAcspn])"
)

RETRO_CORE_UI_SOURCE_FILES = tuple(
    path.relative_to(ROOT)
    for path in sorted((ROOT / "retro-core" / "main").glob("main_*.c"))
)

UI_SOURCE_FILES = (
    Path("launcher/main/applications.c"),
    Path("launcher/main/browser.c"),
    Path("launcher/main/bookmarks.c"),
    Path("launcher/main/gui.c"),
    Path("launcher/main/main.c"),
    Path("launcher/main/updater.c"),
    Path("components/retro-go/rg_gui.c"),
    Path("components/retro-go/rg_system.c"),
    *RETRO_CORE_UI_SOURCE_FILES,
    Path("gwenesis/main/main.c"),
    Path("prboom-go/main/main.c"),
    Path("fmsx/main/main.c"),
)

# These literals are visible but deliberately language-neutral. Protocol keys,
# paths, extensions and native-emulator strings are kept in the per-file list
# below so that adding a broad category cannot silently hide new English UI.
UI_LITERAL_ALLOWLIST = {
    "",
    " ",
    "-",
    "...",
    "???",
    "N/A",
    "Retro-Go",
    "CRC32",
    "Wi-Fi",
    "SSID",
    "IP",
    "UTC",
    "A",
    "B",
    "C",
    "MENU",
    "OPT",
    "SELECT",
    "START",
}

FORMAT_ONLY_LITERAL_RE = re.compile(
    r"^(?:(?:%[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcsp%])|"
    r"[\s\d.,:/+()\[\]<>|=_-])+$"
)

NON_UI_CALLS = {
    "RG_LOGD",
    "RG_LOGE",
    "RG_LOGI",
    "RG_LOGV",
    "RG_LOGW",
    "RG_PANIC",
    "abort",
    "fprintf",
    "printf",
    "puts",
    "rg_system_log",
}

# Exact technical/native strings accepted in each audited source file. Each
# entry was classified by hand; do not replace these with broad prefix/suffix
# rules, because those can hide new user-facing English.
UI_LITERAL_FILE_ALLOWLIST = {
    Path("launcher/main/applications.c"): {
        "%d KB", "/crc32.bin", "CRC32...", "rb", "sav",
        "Nintendo Entertainment System", "Super Nintendo",
        "Nintendo Gameboy", "Nintendo Gameboy Color",
        "Nintendo Gameboy Advance", "Nintendo Game & Watch",
        "Sega Master System", "Sega Game Gear", "Sega Mega Drive",
        "Coleco ColecoVision", "NEC PC Engine", "Atari Lynx", "DOOM", "MSX",
        "nes", "nes fc fds nsf zip", "snes", "smc sfc zip",
        "gb", "gb gbc zip", "gbc", "gbc gb zip", "gba", "gba zip",
        "gw", "gg", "gg zip", "sms", "sms sg zip", "md", "md gen bin zip",
        "col", "col rom zip", "pce", "pce zip", "lnx", "lnx zip",
        "doom", "wad zip", "msx", "rom mx1 mx2 dsk",
        "retro-core", "gbsp", "gwenesis", "prboom-go", "fmsx",
    },
    Path("launcher/main/browser.c"): {"browser"},
    Path("launcher/main/bookmarks.c"): {
        "%s/%s.txt", "favorite", "recent", "n/a", "r", "w",
    },
    Path("launcher/main/gui.c"): {
        "%s.png", "%s_%s.png", "%s/%X/%08X.art", "%s/%X/%08X.png",
        "ABC123", "background", "banner", "foreground", "launcher_1",
        "launcher_2", "launcher_3", "launcher_4", "list_selected_bg",
        "list_selected_fg", "list_standard_bg", "list_standard_fg", "logo", "png",
    },
    Path("launcher/main/main.c"): {
        "/favorite.txt", "/odroid/data", "/odroid/favorite.txt",
        "/odroid/recent.txt", "/recent.txt", "Indicators", "Migration", "launcher",
    },
    Path("launcher/main/updater.c"): {
        "assets", "browser_download_url", "fw img", "html_url", "name",
        "published_at", "wb",
    },
    Path("components/retro-go/rg_gui.c"): {
        "%.1fx", "%.2f%% | %.2fV", "%F %T", "%d (%dMhz)",
        "%ds", "%dx%d", "%s/%s/theme.json",
        "/screenshot.png", "/trace.txt", "ABC", "abc", "ASDFGHJKL ",
        "asdfghjkl ", "QWERTYUIOP", "qwertyuiop", "ZXCVBNM.,?",
        "zxcvbnm.,?", "dialog", "background", "border", "header",
        "item_disabled", "item_message", "item_standard", "none", "retro-go",
        "scrollbar", "shadow", "transparent", "Retro-Go %s", "TZ",
        "UTC-12:00", "UTC-11:00", "UTC-10:00", "UTC-09:00", "UTC-09:30",
        "UTC-08:00", "UTC-07:00", "UTC-06:00", "UTC-05:00", "UTC-04:00",
        "UTC-03:30", "UTC-03:00", "UTC-02:00", "UTC-01:00", "UTC+00:00",
        "UTC+01:00", "UTC+02:00", "UTC+03:00", "UTC+03:30", "UTC+04:00",
        "UTC+04:30", "UTC+05:00", "UTC+05:30", "UTC+06:00", "UTC+06:30",
        "UTC+07:00", "UTC+08:00", "UTC+09:00", "UTC+09:30", "UTC+10:00",
        "UTC+10:30", "UTC+11:00", "UTC+12:00", "UTC+13:00", "UTC+14:00",
    },
    Path("components/retro-go/rg_system.c"): {
        "\n\n*** PANIC TRACE: ***\n\n", "\n\nEnd of trace\n\n",
        "\n*** RG_PANIC() CALLED IN '", "\nLog output:\n", "%s.exe", "(none)",
        ".bak", ".new", ".png", ".sav", ".sram", "/boot.json", "/clock.bin",
        "/crash.log", "/trace.txt", "BootArgs", "BootFlags", "BootName", "EST+5",
        "Ext DAC", "Indicators", "Out of task slots", "TZ", "Timezone", "\\e[0m",
        "LedSystemPattern", "LedLowPattern", "LowBatterySound",
        "\\e[31m", "\\e[33m", "\\e[34m", "\\e[36m", "debug", "error",
        "esp_panic", "info", "main", "rg_sysmon", "rg_system_init() was already called.",
        "stderr.txt", "stdout.txt", "trace", "w", "warn",
    },
    Path("retro-core/main/main_snes.c"): {
        "Type A", "Type B", "Type C", "None", "R", "L", "X", "Right", "Left",
        "Down", "Up", "Start", "Select", "Y", "apu", "keymap", "snes9x  ", "zip",
    },
    Path("retro-core/main/main_nes.c"): {
        "/fds_bios.bin", "autocrop", "overscan", "palette", "spritelimit", "zip",
    },
    Path("retro-core/main/main_gbc.c"): {
        "SaveSRAM", "Palette", "SysTime", "LoadBIOS", "GBC", "DMG   ",
        "Pocket", "Light ", "GBC   ", "SGB   ", "%3ds", "zip",
        "/gbc_bios.bin", "/gb_bios.bin",
    },
    Path("retro-core/main/main_gw.c"): {"wb", "rb"},
    Path("retro-core/main/main_launcher.c"): set(),
    Path("retro-core/main/main_pce.c"): {"overscan", "pce_sound", "zip"},
    Path("retro-core/main/main_sms.c"): {
        "palette", "w", "rb", "sg", "col", "zip",
    },
    Path("prboom-go/main/main.c"): {
        "-file", "-iwad", "-save", "/doom", "Gamma", "doom", "doom_sound", "zip",
    },
    Path("fmsx/main/main.c"): {
        "-diska", "-home", "-joy", "-ram", "-skip", "-vram", "/msx", "Crop",
        "DISK.ROM", "Input", "MSX.ROM", "MSX2.ROM", "MSX2EXT.ROM", "MSXDOS2.ROM",
        "audioTask", "dsk", "fMSX 6.0", "fmsx", "https://fms.komkon.org/fMSX/",
    },
    Path("gwenesis/main/main.c"): {
        "yfm_enable", "z80_enable", "sn_enable", "wb", "rb", "zip",
    },
}

DISPLAY_DESTINATION_HINTS = re.compile(
    r"(?:->|\.)?(?:text|desc|left|right|status|value|name)|"
    r"^(?:header|footer|input_buffer|text_buffer|title|message)$"
)
TECHNICAL_DESTINATION_HINTS = re.compile(
    r"(?:path|url|date|partition|extensions|short_name|configNs|task->name|"
    r"panicTrace|tab->name|text_buffer_ptr|tempname|^name$)"
)
DISPLAY_SINK_CALL_ARGUMENTS = {
    "gui_add_tab": (1,),
    "gui_set_status": (1, 2),
    "rg_gui_alert": (0, 1),
    "rg_gui_confirm": (0, 1),
    "rg_gui_dialog": (0,),
    "rg_gui_draw_message": (0,),
    "rg_gui_draw_text": (3,),
    "rg_gui_file_picker": (0,),
}


def read(path):
    return path.read_text(encoding="utf-8")


def strip_c_comments(source):
    def replace(match):
        token = match.group(0)
        if not token.startswith("/"):
            return token
        return "".join("\n" if char == "\n" else " " for char in token)

    return COMMENT_OR_LITERAL_RE.sub(replace, source)


def mask_c_comments_and_literals(source):
    return COMMENT_OR_LITERAL_RE.sub(
        lambda match: "".join(
            "\n" if char == "\n" else " " for char in match.group(0)
        ),
        source,
    )


def decode_c_strings(expression):
    return "".join(
        decode_c_string_token(match.group(0))
        for match in re.finditer(STRING_TOKEN, expression)
    )


def decode_c_string_token(token):
    # GCC accepts escapes such as \e that Python deliberately warns about.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.literal_eval(token)


def matching_delimiter(masked_source, opening, opening_char, closing_char):
    if masked_source[opening] != opening_char:
        raise AssertionError(f"expected an opening {opening_char}")

    depth = 0
    for index in range(opening, len(masked_source)):
        if masked_source[index] == opening_char:
            depth += 1
        elif masked_source[index] == closing_char:
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError(f"opening {opening_char} has no matching {closing_char}")


def split_top_level_arguments(source, masked_source, opening, closing):
    arguments = []
    start = opening + 1
    paren_depth = brace_depth = bracket_depth = 0

    for index in range(start, closing):
        char = masked_source[index]
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
        elif char == "," and not (paren_depth or brace_depth or bracket_depth):
            arguments.append(source[start:index].strip())
            start = index + 1

    arguments.append(source[start:closing].strip())
    return arguments


def find_calls(source, function_names):
    masked_source = mask_c_comments_and_literals(source)
    names = "|".join(re.escape(name) for name in sorted(function_names, key=len, reverse=True))
    call_re = re.compile(rf"(?<![A-Za-z0-9_])(?P<name>{names})\s*\(")
    calls = []
    for match in call_re.finditer(masked_source):
        opening = masked_source.find("(", match.start())
        closing = matching_delimiter(masked_source, opening, "(", ")")
        calls.append(
            (
                match.group("name"),
                match.start(),
                closing + 1,
                split_top_level_arguments(source, masked_source, opening, closing),
            )
        )
    return calls


def mask_source_ranges(source, ranges):
    masked = list(source)
    for start, end in ranges:
        for index in range(start, end):
            if masked[index] != "\n":
                masked[index] = " "
    return "".join(masked)


def preprocessor_ranges(source):
    ranges = []
    offset = 0
    continuing = False
    for line in source.splitlines(keepends=True):
        is_directive = continuing or line.lstrip().startswith("#")
        if is_directive:
            ranges.append((offset, offset + len(line)))
        continuing = is_directive and line.rstrip().endswith("\\")
        offset += len(line)
    return ranges


def is_allowed_ui_literal(path, literal):
    if literal in UI_LITERAL_ALLOWLIST:
        return True
    if literal in UI_LITERAL_FILE_ALLOWLIST[path]:
        return True
    return bool(FORMAT_ONLY_LITERAL_RE.fullmatch(literal))


def find_unlocalized_ui_literals(source, path):
    source = strip_c_comments(source)
    excluded_ranges = preprocessor_ranges(source)
    excluded_ranges.extend(
        (start, end)
        for _name, start, end, _arguments in find_calls(source, NON_UI_CALLS)
    )
    excluded_ranges.extend(
        (match.start("value"), match.end("value"))
        for match in GETTEXT_LITERAL_RE.finditer(source)
    )
    visible_source = mask_source_ranges(source, excluded_ranges)

    failures = []
    for match in re.finditer(STRING_TOKEN, visible_source):
        literal = decode_c_string_token(match.group(0))
        if re.search(r"[A-Za-z]", literal) and not is_allowed_ui_literal(path, literal):
            failures.append(
                (source.count("\n", 0, match.start()) + 1, literal)
            )
    return failures


def normalized_expression(expression):
    return re.sub(r"\s+", "", expression)


def literal_expression_value(expression):
    expression = strip_c_comments(expression)
    translated = re.fullmatch(
        rf"\s*_\s*\(\s*(?P<value>(?:{STRING_TOKEN}\s*)+)\)\s*",
        expression,
    )
    if translated:
        expression = translated.group("value")
    if not re.fullmatch(rf"\s*(?:{STRING_TOKEN}\s*)+", expression):
        return None
    return decode_c_strings(expression)


def c_function_ranges(masked_source):
    definition_re = re.compile(
        r"(?m)^[ \t]*(?:[A-Za-z_]\w*[\s*]+)+"
        r"(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{"
    )
    ranges = []
    for definition in definition_re.finditer(masked_source):
        if definition.group("name") in {"if", "for", "switch", "while"}:
            continue
        opening = masked_source.find("{", definition.start())
        ranges.append((opening, matching_brace(masked_source, opening)))
    return ranges


def local_display_sink_ranges(source):
    sinks = set()
    masked_source = mask_c_comments_and_literals(source)
    function_ranges = c_function_ranges(masked_source)

    def add_simple_identifier(expression, position):
        identifier = normalized_expression(expression)
        if not re.fullmatch(r"[A-Za-z_]\w*", identifier):
            return
        for opening, closing in function_ranges:
            if opening < position < closing:
                sinks.add((identifier, opening, closing))
                return
        if not function_ranges:
            sinks.add((identifier, 0, len(source)))

    for name, start, _end, arguments in find_calls(
        source, set(DISPLAY_SINK_CALL_ARGUMENTS)
    ):
        for argument_index in DISPLAY_SINK_CALL_ARGUMENTS[name]:
            if argument_index < len(arguments):
                add_simple_identifier(arguments[argument_index], start)

    declaration_re = re.compile(
        r"\b(?:const\s+)?rg_gui_option_t\s+[A-Za-z_]\w*\s*"
        r"\[[^\]]*\]\s*=\s*\{"
    )
    for declaration in declaration_re.finditer(masked_source):
        outer_opening = masked_source.find("{", declaration.start())
        outer_closing = matching_brace(masked_source, outer_opening)
        cursor = outer_opening + 1
        while True:
            opening = masked_source.find("{", cursor, outer_closing)
            if opening < 0:
                break
            closing = matching_brace(masked_source, opening)
            fields = split_top_level_arguments(
                source, masked_source, opening, closing
            )
            for field in fields[1:3]:
                add_simple_identifier(field, declaration.start())
            cursor = closing + 1

    return sinks


def is_display_destination(expression, position, local_sinks=()):
    normalized = normalized_expression(expression)
    if TECHNICAL_DESTINATION_HINTS.search(normalized):
        return False
    local_sink = any(
        identifier == normalized and opening < position < closing
        for identifier, opening, closing in local_sinks
    )
    return local_sink or bool(DISPLAY_DESTINATION_HINTS.search(normalized))


def find_unsafe_display_copies(source):
    failures = []
    local_sinks = local_display_sink_ranges(source)
    for name, start, _end, arguments in find_calls(
        source, {"snprintf", "sprintf", "strcpy", "strncpy", "vsnprintf"}
    ):
        minimum_arguments = {
            "sprintf": 2,
            "strcpy": 2,
            "snprintf": 3,
            "strncpy": 3,
            "vsnprintf": 4,
        }[name]
        if len(arguments) < minimum_arguments:
            continue

        if name in {"snprintf", "vsnprintf"}:
            values = " ".join(arguments[3:])
        elif name == "sprintf":
            values = " ".join(arguments[2:])
        else:
            values = " ".join(arguments[1:2])
        normalized_destination = normalized_expression(arguments[0])
        display_destination = (
            is_display_destination(arguments[0], start, local_sinks)
            or (
                normalized_destination == "buffer"
                and "tab->navpath" in normalized_expression(values)
            )
        )
        if not display_destination:
            continue

        reason = None
        if name in {"sprintf", "strcpy"}:
            reason = f"{name} has no UTF-8 display-buffer bound"
        elif name == "strncpy":
            reason = "strncpy can split a UTF-8 codepoint"
        elif name == "vsnprintf":
            reason = "vsnprintf can split a UTF-8 codepoint"
        else:
            format_value = literal_expression_value(arguments[2])
            string_formats = (
                tuple(
                    token for token in printf_placeholders(format_value)
                    if token.endswith("s")
                )
                if format_value else ()
            )
            if string_formats:
                reason = f"bounded {format_value!r} can split a UTF-8 codepoint"

        if reason:
            failures.append((source.count("\n", 0, start) + 1, reason))
    return failures


def matching_brace(masked_source, opening):
    return matching_delimiter(masked_source, opening, "{", "}")


def translation_array_body(source):
    masked_source = mask_c_comments_and_literals(source)
    declaration = re.search(
        r"static\s+const\s+char\s*\*\s*translations\s*"
        r"\[\s*\]\s*\[\s*RG_LANG_MAX\s*\]\s*=\s*\{",
        masked_source,
    )
    if not declaration:
        raise AssertionError("translations array was not found")
    opening = declaration.end() - 1
    closing = matching_brace(masked_source, opening)
    return source[opening + 1 : closing]


def parse_translation_records(source):
    array_body = translation_array_body(source)
    masked_body = mask_c_comments_and_literals(array_body)
    records = []
    cursor = 0
    while True:
        opening = masked_body.find("{", cursor)
        if opening < 0:
            break
        closing = matching_brace(masked_body, opening)
        record_body = strip_c_comments(array_body[opening + 1 : closing])
        fields = {}
        for language, expression in TRANSLATION_FIELD_RE.findall(record_body):
            if language in fields:
                raise AssertionError(f"duplicate {language} initializer in one record")
            fields[language] = decode_c_strings(expression)
        records.append(fields)
        cursor = closing + 1
    if not records:
        raise AssertionError("no translation records were parsed")
    return records


def translation_records():
    return parse_translation_records(read(TRANSLATIONS_HEADER))


def printf_placeholders(value):
    return tuple(
        token for token in PRINTF_TOKEN_RE.findall(value)
        if token != "%%"
    )


def translation_contract_failures(records):
    failures = []
    for index, fields in enumerate(records, start=1):
        english = fields.get("RG_LANG_EN")
        if english is None:
            continue
        expected_placeholders = printf_placeholders(english)
        expected_newlines = english.count("\n")
        for language in ("RG_LANG_FR", "RG_LANG_DE", "RG_LANG_ZH_CN"):
            value = fields.get(language)
            if value is None:
                continue
            actual_placeholders = printf_placeholders(value)
            if actual_placeholders != expected_placeholders:
                failures.append(
                    (
                        index,
                        language,
                        "placeholders",
                        expected_placeholders,
                        actual_placeholders,
                    )
                )
            actual_newlines = value.count("\n")
            if actual_newlines != expected_newlines:
                failures.append(
                    (
                        index,
                        language,
                        "newlines",
                        expected_newlines,
                        actual_newlines,
                    )
                )
    return failures


def gettext_literals():
    literals = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in CPP_SUFFIXES:
            continue
        source = strip_c_comments(read(path))
        for match in GETTEXT_LITERAL_RE.finditer(source):
            literals.append(
                (
                    path.relative_to(ROOT),
                    source.count("\n", 0, match.start()) + 1,
                    decode_c_strings(match.group("value")),
                )
            )
    return literals


class LocalizationParserTests(unittest.TestCase):
    def test_read_rejects_malformed_utf8(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            malformed = Path(temp_dir) / "malformed.h"
            malformed.write_bytes(b"\xff")

            with self.assertRaises(UnicodeDecodeError):
                read(malformed)

    def test_translation_records_accept_any_record_indentation(self):
        synthetic_catalog = r'''
static const char *translations[][RG_LANG_MAX] =
{
    {
        [RG_LANG_EN] = "Four spaces",
        [RG_LANG_ZH_CN] = "四个空格",
    },
  {
    [RG_LANG_EN] = "Two spaces",
    [RG_LANG_ZH_CN] = "两个空格",
  },
	{
		[RG_LANG_EN] = "Tab",
		[RG_LANG_ZH_CN] = "制表符",
	},
};
'''
        records = parse_translation_records(synthetic_catalog)

        self.assertEqual(
            [record["RG_LANG_EN"] for record in records],
            ["Four spaces", "Two spaces", "Tab"],
        )

    def test_translation_contract_reports_placeholder_and_newline_mismatches(self):
        synthetic_catalog = r'''
static const char *translations[][RG_LANG_MAX] = {
    {
        [RG_LANG_EN] = "Value %d\n%s",
        [RG_LANG_FR] = "Value %d\n%s",
        [RG_LANG_DE] = "Value %d\n%s",
        [RG_LANG_ZH_CN] = "值 %s",
    },
};
'''

        failures = translation_contract_failures(
            parse_translation_records(synthetic_catalog)
        )

        self.assertEqual(
            failures,
            [
                (1, "RG_LANG_ZH_CN", "placeholders", ("%d", "%s"), ("%s",)),
                (1, "RG_LANG_ZH_CN", "newlines", 1, 0),
            ],
        )

    def test_ui_literal_scanner_catches_calls_tabs_and_menu_structs(self):
        synthetic_source = r'''
rg_gui_draw_message("Connecting...");
rg_gui_alert("Download failed!", "Read/write error!");
gui_add_tab("browser", "File Manager", NULL, event_handler);
const rg_gui_option_t options[] = {
    {0, "Compute", NULL, RG_DIALOG_FLAG_NORMAL, NULL},
};
RG_LOGI("This diagnostic is not visible UI");
rg_gui_draw_message(_("Already translated"));
'''
        path = Path("launcher/main/browser.c")

        self.assertEqual(
            [literal for _line, literal in find_unlocalized_ui_literals(synthetic_source, path)],
            [
                "Connecting...",
                "Download failed!",
                "Read/write error!",
                "File Manager",
                "Compute",
            ],
        )

    def test_display_copy_scanner_catches_byte_truncation_patterns(self):
        synthetic_source = r'''
snprintf(item->text, sizeof(item->text), "[%.40s]", file->name);
snprintf(option->value, sizeof(option->value), "%s", release->name);
strncpy(input_buffer, default_value, sizeof(input_buffer) - 1);
strcpy(option->value, _("Translated value"));
snprintf(path, sizeof(path), "%s/%s", folder, file->name);
snprintf(name, sizeof(name), "%s.png", type);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [2, 3, 4, 5])

    def test_display_copy_scanner_catches_unbounded_sprintf(self):
        synthetic_source = r'''
sprintf(display->text, _("Translated value"));
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [2])

    def test_display_copy_scanner_catches_star_precision(self):
        synthetic_source = r'''
snprintf(display->text, sizeof(display->text), "%.*s", limit, payload);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [2])

    def test_display_copy_scanner_decodes_translated_string_formats(self):
        synthetic_source = r'''
snprintf(display->text, sizeof(display->text), _("%s"), dynamic_name);
snprintf(display->text, sizeof(display->text), _("%s" " (%d)"), dynamic_name, count);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [2, 3])
        self.assertIn("'%s (%d)'", failures[1][1])

    def test_display_copy_scanner_catches_plain_string_payloads(self):
        synthetic_source = r'''
snprintf(option->value, sizeof(option->value), "%s", payload);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [2])

    def test_display_copy_scanner_follows_local_dialog_and_call_sinks(self):
        synthetic_source = r'''
char dialog_buffer[32];
char drawn_buffer[32];
const rg_gui_option_t options[] = {
    {0, dialog_buffer, NULL, RG_DIALOG_FLAG_MESSAGE, NULL},
    RG_DIALOG_END,
};
snprintf(dialog_buffer, sizeof(dialog_buffer), "%s", payload);
snprintf(drawn_buffer, sizeof(drawn_buffer), "%s", payload);
rg_gui_draw_text(0, 0, 0, drawn_buffer, 0, 0, 0);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [8, 9])

    def test_display_copy_scanner_catches_vsnprintf_to_a_local_ui_sink(self):
        synthetic_source = r'''
char buffer[32];
const rg_gui_option_t options[] = {
    {0, buffer, NULL, RG_DIALOG_FLAG_MESSAGE, NULL},
    RG_DIALOG_END,
};
vsnprintf(buffer, sizeof(buffer), format, args);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [7])

    def test_local_display_sinks_do_not_leak_across_function_scopes(self):
        synthetic_source = r'''
void draw_dialog(void) {
    char buffer[32];
    const rg_gui_option_t options[] = {
        {0, buffer, NULL, RG_DIALOG_FLAG_MESSAGE, NULL},
        RG_DIALOG_END,
    };
    vsnprintf(buffer, sizeof(buffer), format, args);
}
void build_path(void) {
    char buffer[RG_PATH_MAX];
    snprintf(buffer, sizeof(buffer), "%s/%s", folder, filename);
}
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [8])

    def test_literal_expression_decodes_comment_separated_translated_literals(self):
        self.assertEqual(
            literal_expression_value('_("%s" /* translator note */ " (%d)")'),
            "%s (%d)",
        )

    def test_display_copy_scanner_ignores_escaped_percent_text(self):
        synthetic_source = r'''
snprintf(option->value, sizeof(option->value), "%%.40s", payload);
'''

        self.assertEqual(find_unsafe_display_copies(synthetic_source), [])

    def test_display_copy_scanner_catches_common_local_display_buffers(self):
        synthetic_source = r'''
char buffer[16], filesize[16], filecrc[16], song[16];
const rg_gui_option_t options[] = {
    {0, buffer, NULL, RG_DIALOG_FLAG_MESSAGE, NULL},
    {0, "Size", filesize, RG_DIALOG_FLAG_NORMAL, NULL},
    {0, "CRC", filecrc, RG_DIALOG_FLAG_NORMAL, NULL},
    {0, "Song", song, RG_DIALOG_FLAG_NORMAL, NULL},
    RG_DIALOG_END,
};
sprintf(buffer, "%02d:%02d", hour, minute);
sprintf(filesize, "%d KB", size);
sprintf(filecrc, "%08X", checksum);
sprintf(song, "%d / %d", current_song, total_songs);
'''

        failures = find_unsafe_display_copies(synthetic_source)

        self.assertEqual([line for line, _reason in failures], [10, 11, 12, 13])


class VisibleUiLocalizationTests(unittest.TestCase):
    def test_theme_name_storage_accepts_a_full_path_component(self):
        source = strip_c_comments(read(RETRO_GO / "rg_gui.c"))
        self.assertRegex(source, r"\bchar\s+theme_name\s*\[\s*RG_PATH_MAX\s*\]")

    def test_theme_image_path_is_not_limited_to_a_fixed_buffer(self):
        source = strip_c_comments(read(RETRO_GO / "rg_gui.c"))
        function = re.search(
            r"rg_image_t\s*\*rg_gui_get_theme_image\b(?P<body>.*?)(?=\n}\n)",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(function)
        body = function.group("body")
        self.assertNotRegex(body, r"\bchar\s+pathbuf\s*\[")
        self.assertRegex(body, r"\bmalloc\s*\(")
        self.assertRegex(body, r"\bfree\s*\(")

    def test_audited_ui_sources_have_no_untranslated_english_literals(self):
        failures = []
        for path in UI_SOURCE_FILES:
            for line, literal in find_unlocalized_ui_literals(read(ROOT / path), path):
                failures.append(f"{path}:{line}: {literal!r}")
        self.assertFalse(
            failures,
            "untranslated English UI literals:\n" + "\n".join(failures),
        )

    def test_audited_ui_display_copies_preserve_utf8_boundaries(self):
        failures = []
        for path in UI_SOURCE_FILES:
            for line, reason in find_unsafe_display_copies(read(ROOT / path)):
                failures.append(f"{path}:{line}: {reason}")
        self.assertFalse(
            failures,
            "unsafe UTF-8 display copies:\n" + "\n".join(failures),
        )

    def test_snes_dynamic_names_are_localized_at_display_time(self):
        source = strip_c_comments(read(ROOT / "retro-core/main/main_snes.c"))
        self.assertRegex(source, r"_\s*\(\s*keymap\.name\s*\)")
        self.assertGreaterEqual(
            len(re.findall(r"_\s*\(\s*rg_input_get_key_name\s*\(", source)),
            2,
        )
        self.assertRegex(source, r"option->label\s*=\s*_\s*\(\s*SNES_BUTTONS\s*\[")

    def test_snes_dynamic_display_names_have_catalog_records(self):
        input_source = strip_c_comments(read(RETRO_GO / "rg_input.c"))
        snes_source = strip_c_comments(read(ROOT / "retro-core/main/main_snes.c"))
        key_function = re.search(
            r"rg_input_get_key_name\s*\([^)]*\)\s*\{(?P<body>.*?)\n\}",
            input_source,
            re.DOTALL,
        )
        self.assertIsNotNone(key_function)
        key_names = {
            decode_c_string_token(token)
            for token in re.findall(
                r"\breturn\s+(" + STRING_TOKEN + r")",
                key_function.group("body"),
            )
        }
        buttons_match = re.search(
            r"SNES_BUTTONS\s*\[\s*\]\s*=\s*\{(?P<body>.*?)\};",
            snes_source,
            re.DOTALL,
        )
        self.assertIsNotNone(buttons_match)
        button_names = {
            decode_c_string_token(match.group(0))
            for match in re.finditer(STRING_TOKEN, buttons_match.group("body"))
        }
        language_neutral = {"A", "B", "L", "R", "X", "Y"}
        catalog_keys = {
            fields["RG_LANG_EN"]
            for fields in translation_records()
            if "RG_LANG_EN" in fields
        }

        self.assertEqual((key_names | button_names) - language_neutral - catalog_keys, set())

    def test_bookmark_prefix_preserves_full_internal_app_type(self):
        source = strip_c_comments(read(ROOT / "launcher/main/bookmarks.c"))

        self.assertRegex(
            source,
            r"rg_utf8_copy\s*\(\s*listitem->text\s*\+\s*prefix_length\s*,"
            r"[^;]*\btype\s*\)",
        )
        self.assertRegex(source, r"while\s*\(\s*prefix_length\s*<\s*4\s*\)")


class LocalizationCatalogTests(unittest.TestCase):
    def test_chinese_menu_wording_is_precise(self):
        by_english = {
            fields["RG_LANG_EN"]: fields["RG_LANG_ZH_CN"]
            for fields in translation_records()
        }
        self.assertEqual(by_english["Crop sides"], "裁剪两侧")
        self.assertEqual(by_english["Fit"], "适配")
        self.assertEqual(by_english["Load game"], "载入存档")
        self.assertEqual(by_english["Reset Emulation?"], "重置模拟器？")
        self.assertEqual(by_english["%dms (block: %dms)"], "%dms（阻塞：%dms）")

    def test_language_enum_and_display_names_include_simplified_chinese(self):
        header = strip_c_comments(read(LOCALIZATION_HEADER))
        enum_match = re.search(
            r"typedef\s+enum\s*\{(?P<body>.*?)\}\s*rg_language_t\s*;",
            header,
            re.DOTALL,
        )
        self.assertIsNotNone(enum_match, "rg_language_t enum was not found")
        enum_members = re.findall(
            r"\b(RG_LANG_[A-Z_]+)\b\s*(?:=\s*([^,\s]+))?\s*,?",
            enum_match.group("body"),
        )
        self.assertEqual(
            enum_members,
            [
                ("RG_LANG_EN", "0"),
                ("RG_LANG_FR", ""),
                ("RG_LANG_DE", ""),
                ("RG_LANG_ZH_CN", ""),
                ("RG_LANG_MAX", ""),
            ],
        )

        translations = read(TRANSLATIONS_HEADER)
        names_match = re.search(
            r"language_names\[RG_LANG_MAX\]\s*=\s*\{(?P<body>.*?)\};",
            translations,
            re.DOTALL,
        )
        self.assertIsNotNone(names_match, "language_names array was not found")
        names = {
            language: decode_c_strings(expression)
            for language, expression in TRANSLATION_FIELD_RE.findall(
                names_match.group("body")
            )
        }
        self.assertEqual(names.get("RG_LANG_EN"), "English")
        self.assertEqual(names.get("RG_LANG_FR"), "Francais")
        self.assertEqual(names.get("RG_LANG_DE"), "Deutsch")
        self.assertEqual(names.get("RG_LANG_ZH_CN"), "简体中文")

    def test_microbyte_is_the_only_target_with_a_chinese_default(self):
        expected_define = re.compile(
            r"^\s*#\s*define\s+RG_LANG_DEFAULT\s+RG_LANG_ZH_CN\s*$",
            re.MULTILINE,
        )
        self.assertEqual(len(expected_define.findall(read(MICROBYTE_CONFIG))), 1)

    def test_microbyte_fatfs_api_uses_utf8(self):
        sdkconfig = read(MICROBYTE_SDKCONFIG)

        self.assertRegex(sdkconfig, r"(?m)^CONFIG_FATFS_API_ENCODING_UTF_8=y$")
        self.assertNotRegex(
            sdkconfig,
            r"(?m)^CONFIG_FATFS_API_ENCODING_(?:ANSI_OEM|UTF_16)=y$",
        )

    def test_microbyte_main_task_stack_is_at_least_8kb(self):
        sdkconfig = read(MICROBYTE_SDKCONFIG)
        match = re.search(r"(?m)^CONFIG_ESP_MAIN_TASK_STACK_SIZE=(\d+)$", sdkconfig)

        self.assertIsNotNone(match)
        self.assertGreaterEqual(int(match.group(1)), 8192)

        definitions = []
        for target_config in sorted((RETRO_GO / "targets").glob("*/config.h")):
            if re.search(
                r"^\s*#\s*define\s+RG_LANG_DEFAULT\b",
                read(target_config),
                re.MULTILINE,
            ):
                definitions.append(target_config.relative_to(RETRO_GO))
        self.assertEqual(definitions, [Path("targets/microbyte/config.h")])

        shared = read(SHARED_CONFIG)
        include_position = shared.index('#include "targets/microbyte/config.h"')
        fallback_match = re.search(
            r"#ifndef\s+RG_LANG_DEFAULT\s*\n"
            r"#define\s+RG_LANG_DEFAULT\s+RG_LANG_EN\s*\n"
            r"#endif",
            shared,
        )
        self.assertIsNotNone(fallback_match, "shared English fallback changed")
        self.assertLess(include_position, fallback_match.start())

    def test_every_translation_record_has_all_nonempty_languages(self):
        source = read(TRANSLATIONS_HEADER)
        records = parse_translation_records(source)
        english_initializer_count = len(
            re.findall(
                r"\[\s*RG_LANG_EN\s*\]\s*=",
                strip_c_comments(translation_array_body(source)),
            )
        )
        self.assertEqual(
            len(records),
            english_initializer_count,
            "parsed record count differs from RG_LANG_EN initializer count",
        )
        missing = []
        required_languages = {
            "RG_LANG_EN",
            "RG_LANG_FR",
            "RG_LANG_DE",
            "RG_LANG_ZH_CN",
        }
        for index, fields in enumerate(records, start=1):
            english = fields.get("RG_LANG_EN", f"record {index}")
            for language in sorted(required_languages):
                value = fields.get(language)
                if value is None or not value.strip():
                    missing.append(f"{index}: {english!r}: {language}")
        self.assertFalse(
            missing,
            "records with missing/empty language fields:\n" + "\n".join(missing),
        )

    def test_translation_placeholders_and_newlines_match_english(self):
        failures = translation_contract_failures(translation_records())

        self.assertFalse(
            failures,
            "translation format contract mismatches:\n"
            + "\n".join(map(str, failures)),
        )

    def test_every_gettext_literal_has_an_english_catalog_key(self):
        catalog_keys = {
            fields["RG_LANG_EN"]
            for fields in translation_records()
            if "RG_LANG_EN" in fields
        }
        missing = []
        seen = set()
        for path, line, literal in gettext_literals():
            if literal not in catalog_keys and literal not in seen:
                missing.append(f"{path}:{line}: {literal!r}")
                seen.add(literal)
        self.assertFalse(
            missing,
            "_() literals missing from the English catalog:\n" + "\n".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
