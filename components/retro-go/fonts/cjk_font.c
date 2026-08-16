#include "cjk_font.h"

#ifdef RG_CJK_FULL
#include "cjk_gb2312_data.inc"
#else
#include "cjk_menu_data.inc"
#endif

#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))
#define CJK_SOURCE_POINTS 12
#define CJK_MAX_POINTS 32

bool rg_cjk_get_glyph(uint16_t codepoint, const uint8_t **bitmap)
{
    size_t lower = 0;
    size_t upper = ARRAY_SIZE(cjk_codepoints);

    if (bitmap != NULL)
        *bitmap = NULL;

    while (lower < upper)
    {
        const size_t middle = lower + (upper - lower) / 2;
        if (cjk_codepoints[middle] < codepoint)
            lower = middle + 1;
        else
            upper = middle;
    }

    if (lower >= ARRAY_SIZE(cjk_codepoints) || cjk_codepoints[lower] != codepoint)
        return false;

    if (bitmap != NULL)
        *bitmap = cjk_bitmaps[lower];
    return true;
}

size_t rg_cjk_render_glyph(uint32_t *rows, int points, uint16_t codepoint)
{
    const uint8_t *bitmap;

    if (points <= 0)
        points = CJK_SOURCE_POINTS;
    if (!rg_cjk_get_glyph(codepoint, &bitmap))
        return 0;

    const int glyph_points = points > CJK_MAX_POINTS ? CJK_MAX_POINTS : points;
    if (rows == NULL)
        return (size_t)glyph_points;

    for (int y = 0; y < points; ++y)
        rows[y] = 0;

    const int y_offset = (points - glyph_points) / 2;

    for (int y = 0; y < glyph_points; ++y)
    {
        const unsigned source_y = (unsigned)y * CJK_SOURCE_POINTS / (unsigned)glyph_points;
        uint32_t row = 0;

        for (int x = 0; x < glyph_points; ++x)
        {
            const unsigned source_x = (unsigned)x * CJK_SOURCE_POINTS / (unsigned)glyph_points;
            const unsigned bit = source_y * CJK_SOURCE_POINTS + source_x;
            if ((bitmap[bit / 8] & (UINT32_C(0x80) >> (bit % 8))) != 0)
                row |= UINT32_C(1) << (unsigned)x;
        }
        rows[y_offset + y] = row;
    }

    return (size_t)glyph_points;
}
