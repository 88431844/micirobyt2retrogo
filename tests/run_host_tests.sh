#!/bin/sh

set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/retro-go-host-tests.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM

run_utf8()
{
    "${CC:-cc}" \
        -std=c99 -Wall -Wextra -Werror -pedantic \
        -I"$repo_root/components/retro-go" \
        "$repo_root/tests/test_utf8.c" \
        "$repo_root/components/retro-go/rg_utf8.c" \
        -o "$build_dir/test_utf8"
    "$build_dir/test_utf8"
}

run_cjk_variant()
{
    variant=$1
    shift
    "${CC:-cc}" \
        -std=c99 -Wall -Wextra -Werror -pedantic \
        "$@" \
        -I"$repo_root/components/retro-go" \
        "$repo_root/tests/test_cjk_font.c" \
        "$repo_root/components/retro-go/fonts/cjk_font.c" \
        -o "$build_dir/test_cjk_$variant"
    "$build_dir/test_cjk_$variant"
}

run_cjk()
{
    run_cjk_variant menu
    run_cjk_variant full -DRG_CJK_FULL=1
}

run_gui_defaults()
{
    "${CC:-cc}" \
        -std=c99 -Wall -Wextra -Werror -pedantic \
        -I"$repo_root/components/retro-go" \
        "$repo_root/tests/test_gui_defaults.c" \
        "$repo_root/components/retro-go/rg_gui_defaults.c" \
        -o "$build_dir/test_gui_defaults"
    "$build_dir/test_gui_defaults"
}

case "${1:-all}" in
    utf8)
        run_utf8
        ;;
    cjk)
        run_cjk
        ;;
    gui-defaults)
        run_gui_defaults
        ;;
    all)
        run_utf8
        run_cjk
        run_gui_defaults
        ;;
    *)
        echo "usage: $0 {utf8|cjk|gui-defaults|all}" >&2
        exit 2
        ;;
esac
