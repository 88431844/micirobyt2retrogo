#include "fonts/cjk_font.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef RG_CJK_FULL
#include "fonts/cjk_gb2312_data.inc"
#else
#include "fonts/cjk_menu_data.inc"
#endif

#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))

static int failures;

#define CHECK(condition)                                                        \
    do                                                                          \
    {                                                                           \
        if (!(condition))                                                       \
        {                                                                       \
            fprintf(stderr, "%s:%d: check failed: %s\n", __FILE__, __LINE__,  \
                    #condition);                                                \
            failures++;                                                         \
        }                                                                       \
    } while (0)

static uint16_t find_missing_codepoint(void)
{
    for (size_t i = 1; i < ARRAY_SIZE(cjk_codepoints); ++i)
    {
        if ((uint32_t)cjk_codepoints[i - 1] + 1 < cjk_codepoints[i])
            return (uint16_t)(cjk_codepoints[i - 1] + 1);
    }
    return 0;
}

static void test_lookup_first_middle_and_last(void)
{
    const size_t indexes[] = {0, ARRAY_SIZE(cjk_codepoints) / 2,
                              ARRAY_SIZE(cjk_codepoints) - 1};

    for (size_t i = 0; i < ARRAY_SIZE(indexes); ++i)
    {
        const size_t index = indexes[i];
        const uint8_t *bitmap = NULL;

        CHECK(rg_cjk_get_glyph(cjk_codepoints[index], &bitmap));
        CHECK(bitmap != NULL);
        if (bitmap != NULL)
            CHECK(memcmp(bitmap, cjk_bitmaps[index], sizeof(cjk_bitmaps[index])) == 0);
    }
}

static void test_lookup_with_null_bitmap(void)
{
    CHECK(rg_cjk_get_glyph(cjk_codepoints[ARRAY_SIZE(cjk_codepoints) / 2], NULL));
}

static void test_lookup_missing_codepoint(void)
{
    const uint16_t missing = find_missing_codepoint();
    const uint8_t *bitmap = (const uint8_t *)(uintptr_t)1;

    CHECK(missing != 0);
    CHECK(!rg_cjk_get_glyph(missing, &bitmap));
    CHECK(bitmap == NULL);
    CHECK(!rg_cjk_get_glyph(missing, NULL));
}

static void test_lookup_before_first_and_after_last(void)
{
    const size_t last = ARRAY_SIZE(cjk_codepoints) - 1;
    const uint8_t *bitmap = (const uint8_t *)(uintptr_t)1;

    CHECK(cjk_codepoints[0] > 0);
    CHECK(!rg_cjk_get_glyph((uint16_t)(cjk_codepoints[0] - 1), &bitmap));
    CHECK(bitmap == NULL);

    bitmap = (const uint8_t *)(uintptr_t)1;
    CHECK(cjk_codepoints[last] < UINT16_MAX);
    CHECK(!rg_cjk_get_glyph((uint16_t)(cjk_codepoints[last] + 1), &bitmap));
    CHECK(bitmap == NULL);
}

static void test_render_at_source_size(void)
{
    uint32_t rows[12];
    const uint32_t expected[12] = {
        0, 0, 0, 0, 0, 0, 0, UINT32_C(0x002), UINT32_C(0x006),
        UINT32_C(0x00C), 0, 0,
    };

    memset(rows, 0xFF, sizeof(rows));
    CHECK(rg_cjk_render_glyph(rows, 12, 0x3001) == 12);
    CHECK(memcmp(rows, expected, sizeof(expected)) == 0);
}

static void test_render_scaled(void)
{
    uint32_t rows[24];
    uint32_t expected[24] = {0};

    expected[14] = expected[15] = UINT32_C(0x00000C);
    expected[16] = expected[17] = UINT32_C(0x00003C);
    expected[18] = expected[19] = UINT32_C(0x0000F0);

    memset(rows, 0xFF, sizeof(rows));
    CHECK(rg_cjk_render_glyph(rows, 24, 0x3001) == 24);
    CHECK(memcmp(rows, expected, sizeof(expected)) == 0);
}

static void test_render_at_32_points_uses_bit_31_without_overflow(void)
{
    uint32_t guarded_rows[34];
    bool bit_31_set = false;

    for (size_t i = 0; i < ARRAY_SIZE(guarded_rows); ++i)
        guarded_rows[i] = UINT32_C(0xA5A5A5A5);

    CHECK(rg_cjk_render_glyph(&guarded_rows[1], 32, 0x4E00) == 32);
    CHECK(guarded_rows[0] == UINT32_C(0xA5A5A5A5));
    CHECK(guarded_rows[33] == UINT32_C(0xA5A5A5A5));

    for (size_t y = 1; y <= 32; ++y)
    {
        if ((guarded_rows[y] & (UINT32_C(1) << 31)) != 0)
            bit_31_set = true;
    }
    CHECK(bit_31_set);
}

static void test_render_at_33_points_clamps_and_clears_extra_row(void)
{
    uint32_t rows_32[32];
    uint32_t rows_33[33];

    CHECK(rg_cjk_render_glyph(rows_32, 32, 0x3001) == 32);
    memset(rows_33, 0xA5, sizeof(rows_33));
    CHECK(rg_cjk_render_glyph(rows_33, 33, 0x3001) == 32);
    CHECK(memcmp(rows_33, rows_32, sizeof(rows_32)) == 0);
    CHECK(rows_33[32] == 0);
    CHECK(rg_cjk_render_glyph(NULL, 33, 0x3001) == 32);
}

static void test_render_at_34_points_centers_and_clears_padding(void)
{
    uint32_t rows_32[32];
    uint32_t rows_34[34];

    CHECK(rg_cjk_render_glyph(rows_32, 32, 0x3001) == 32);
    memset(rows_34, 0xA5, sizeof(rows_34));
    CHECK(rg_cjk_render_glyph(rows_34, 34, 0x3001) == 32);
    CHECK(rows_34[0] == 0);
    CHECK(memcmp(&rows_34[1], rows_32, sizeof(rows_32)) == 0);
    CHECK(rows_34[33] == 0);
    CHECK(rg_cjk_render_glyph(NULL, 34, 0x3001) == 32);
}

static void test_render_width_and_bounds(void)
{
    const uint16_t missing = find_missing_codepoint();
    uint32_t rows[32];

    CHECK(rg_cjk_render_glyph(NULL, 12, 0x3001) == 12);
    CHECK(rg_cjk_render_glyph(NULL, 24, 0x3001) == 24);
    CHECK(rg_cjk_render_glyph(NULL, 0, 0x3001) == 12);
    CHECK(rg_cjk_render_glyph(NULL, -1, 0x3001) == 12);
    CHECK(rg_cjk_render_glyph(NULL, 12, missing) == 0);

    for (size_t i = 0; i < ARRAY_SIZE(rows); ++i)
        rows[i] = UINT32_C(0xA5A5A5A5);
    CHECK(rg_cjk_render_glyph(rows, 12, missing) == 0);
    CHECK(rows[0] == UINT32_C(0xA5A5A5A5));
}

int main(void)
{
    test_lookup_first_middle_and_last();
    test_lookup_with_null_bitmap();
    test_lookup_missing_codepoint();
    test_lookup_before_first_and_after_last();
    test_render_at_source_size();
    test_render_scaled();
    test_render_at_32_points_uses_bit_31_without_overflow();
    test_render_at_33_points_clamps_and_clears_extra_row();
    test_render_at_34_points_centers_and_clears_padding();
    test_render_width_and_bounds();

    if (failures != 0)
    {
        fprintf(stderr, "CJK font tests failed: %d\n", failures);
        return 1;
    }

#ifdef RG_CJK_FULL
    puts("CJK full font tests passed");
#else
    puts("CJK menu font tests passed");
#endif
    return 0;
}
