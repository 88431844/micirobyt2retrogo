#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool rg_cjk_get_glyph(uint16_t codepoint, const uint8_t **bitmap);
size_t rg_cjk_render_glyph(uint32_t *rows, int points, uint16_t codepoint);
